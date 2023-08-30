"""segment glb with draco compression"""
import argparse
import io
import struct
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import DracoPy
import numpy as np
from gltflib import (
    Accessor,
    AccessorType,
    Asset,
    Attributes,
    Buffer,
    BufferTarget,
    BufferView,
    ComponentType,
    GLTFModel,
    Mesh,
    Primitive,
    Material,
    Image,
    Texture,
)
from gltflib.gltf import GLTF
from gltflib.gltf_resource import GLTFResource, GLBResource, FileResource
from PIL import Image as PIL_Image
from tqdm import tqdm

from typing import Optional, Union


@dataclass
class MeshData:
    """MeshData"""

    points: Optional[np.ndarray]
    faces: Optional[np.ndarray]
    tex_coord: Optional[np.ndarray]

    def all(self) -> bool:
        """returns true if all data is present"""
        return all(
            [
                self.points is not None,
                self.faces is not None,
                self.tex_coord is not None,
            ]
        )


class SubmeshSegment:
    """SubmeshSegment"""

    points: np.ndarray
    tex_coord: np.ndarray

    def __init__(self) -> None:
        self.vertices: list[np.ndarray] = []
        self.faces: list[np.ndarray] = []
        self.uv_coords: list[np.ndarray] = []
        self.vertex_map: dict[int, int] = {}

    def add_face(self, face: np.ndarray) -> None:
        """adds face"""
        new_face: list[int] = []
        for vertex in face:
            if vertex not in self.vertex_map:
                self.vertex_map[vertex] = len(self.vertices)
                self.vertices.append(self.points[vertex])
                self.uv_coords.append(self.tex_coord[vertex])
            new_face.append(self.vertex_map[vertex])
        self.faces.append(np.array(new_face))

    def to_dict(self) -> dict[str, np.ndarray]:
        """returns dict"""
        return {
            "vertices": np.array(self.vertices),
            "faces": np.array(self.faces),
            "uv_coords": np.array(self.uv_coords),
        }

    def to_mesh_data(self) -> MeshData:
        """returns mesh data"""
        return MeshData(
            points=np.array(self.vertices),
            faces=np.array(self.faces),
            tex_coord=np.array(self.uv_coords),
        )


class BufferAccessor:
    """BufferAccessor"""

    glb: GLTF

    def get_accessor(
        self, accessor_index: Optional[int]
    ) -> Optional[Accessor]:
        """returns accessor"""
        if accessor_index is None:
            return None
        return self._get_accessor(accessor_index)

    def _get_accessor(self, accessor_index: int) -> Accessor:
        """returns accessor"""
        accessors: Optional[list[Accessor]] = self.glb.model.accessors
        if accessors is None:
            raise ValueError("No accessors found")
        if accessor_index >= len(accessors):
            raise ValueError("Accessor index out of range")
        return accessors[accessor_index]

    def get_buffer_data(self, buffer: Buffer) -> bytes:
        """get the data from a buffer"""
        resource: Union[GLBResource, GLTFResource] = (
            self.glb.get_glb_resource()
            if buffer.uri is None
            else self.glb.get_resource(buffer.uri)
        )
        if isinstance(resource, FileResource):
            resource.load()
        return resource.data

    def retrieve_bufferview(self, buffer_view_index: int) -> bytes:
        """returns buffer data"""
        buffer_views: Optional[list[BufferView]] = self.glb.model.bufferViews
        if buffer_views is None:
            raise ValueError("No buffer views found")
        if buffer_view_index >= len(buffer_views):
            raise ValueError("Buffer view index out of range")
        buffer_view: BufferView = buffer_views[buffer_view_index]
        buffers: Optional[list[Buffer]] = self.glb.model.buffers
        if buffers is None:
            raise ValueError("No buffers found")
        buffer: Buffer = buffers[buffer_view.buffer]
        data: bytes = self.get_buffer_data(buffer)
        start: int = buffer_view.byteOffset or 0
        end: int = start + buffer_view.byteLength
        return data[start:end]

    def access_buffer(self, accessor_index: Optional[int]) -> bytes:
        """returns buffer data"""
        if accessor_index is None:
            return b""
        accessor: Accessor = self._get_accessor(accessor_index)
        if accessor.bufferView is None:
            raise ValueError("No buffer view found")
        return self.retrieve_bufferview(accessor.bufferView)


class _Attributes(BufferAccessor):
    """Attributes of a primitive, containing accessors to the data"""

    def __init__(self, attributes: Attributes) -> None:
        self.attributes: Attributes = attributes

    @property
    def position(self) -> Optional[Accessor]:
        """returns position"""
        return self.get_accessor(self.attributes.POSITION)

    @property
    def normal(self) -> Optional[Accessor]:
        """returns normal"""
        return self.get_accessor(self.attributes.NORMAL)

    @property
    def tangent(self) -> Optional[Accessor]:
        """returns tangent"""
        return self.get_accessor(self.attributes.TANGENT)

    @property
    def texcoord_0(self) -> Optional[Accessor]:
        """returns texcoord_0"""
        return self.get_accessor(self.attributes.TEXCOORD_0)

    @property
    def texcoord_1(self) -> Optional[Accessor]:
        """returns texcoord_1"""
        return self.get_accessor(self.attributes.TEXCOORD_1)

    @property
    def color_0(self) -> Optional[Accessor]:
        """returns color_0"""
        return self.get_accessor(self.attributes.COLOR_0)

    @property
    def joints_0(self) -> Optional[Accessor]:
        """returns joints_0"""
        return self.get_accessor(self.attributes.JOINTS_0)

    @property
    def weights_0(self) -> Optional[Accessor]:
        """returns weights_0"""
        return self.get_accessor(self.attributes.WEIGHTS_0)


class MeshSegment(BufferAccessor):
    """MeshSegment"""

    def __init__(self, primitive: Primitive) -> None:
        self.attributes: _Attributes = _Attributes(primitive.attributes)
        self.indices: Optional[Accessor] = self.get_accessor(primitive.indices)
        self.material: Optional[Material]
        self.set_material(primitive.material)
        self.data: MeshData = self._get_data()
        self.seg: np.ndarray = np.array([])
        self.vertices_to_class = defaultdict(lambda: -1)

    @property
    def submeshes(self) -> dict[int, SubmeshSegment]:
        """returns submeshes"""
        if not hasattr(self, "_submeshes") or self._submeshes is None:
            self._submeshes: dict[int, SubmeshSegment] = self._get_submeshes()
        return self._submeshes

    @submeshes.setter
    def submeshes(self, submeshes: dict[int, SubmeshSegment]) -> None:
        """sets submeshes"""
        self._submeshes = submeshes

    def set_material(self, material_index: Optional[int]) -> None:
        """sets material"""
        if material_index is None:
            self.material = None
            return
        materials: Optional[list[Material]] = self.glb.model.materials
        if materials is None:
            raise ValueError("No materials found")
        if material_index >= len(materials):
            raise ValueError("Material index out of range")
        self.material = materials[material_index]

    def get_texture_image_bytes(self) -> Optional[bytes]:
        """returns texture image bytes"""
        if (
            self.material is None
            or self.material.pbrMetallicRoughness is None
            or self.material.pbrMetallicRoughness.baseColorTexture is None
        ):
            return None
        texture_index: int = (
            self.material.pbrMetallicRoughness.baseColorTexture.index
        )
        textures: Optional[list[Texture]] = self.glb.model.textures
        if textures is None or texture_index >= len(textures):
            return None
        texture: Texture = textures[texture_index]
        if texture.source is None:
            return None
        image_index: int = texture.source
        images: Optional[list[Image]] = self.glb.model.images
        if images is None or image_index >= len(images):
            return None
        image: Image = images[image_index]
        if image.bufferView is None:
            return None
        return self.retrieve_bufferview(image.bufferView)

    def get_texture_image(self) -> Optional[PIL_Image.Image]:
        """returns texture image"""
        data: Optional[bytes] = self.get_texture_image_bytes()
        if data is None:
            return None
        return PIL_Image.open(io.BytesIO(data))

    def _get_data(self) -> MeshData:
        data: MeshData = self.retrieve_data()
        if data.all():
            return data
        try_data = self.try_finding_data()
        if try_data:
            return try_data
        raise ValueError("No data found")

    def retrieve_data(self) -> MeshData:
        """retrieves data from attributes accessors"""
        points: Optional[np.ndarray] = None  # vec3 float
        faces: Optional[np.ndarray] = None  # vec3 int
        tex: Optional[np.ndarray] = None  # vec2 float
        attr: _Attributes = self.attributes
        if attr.position and attr.position.bufferView:
            index: int = attr.position.bufferView
            buffer: bytes = self.access_buffer(index)
            points = np.frombuffer(buffer, dtype=np.float32).reshape(-1, 3)
        if self.indices and self.indices.bufferView:
            index = self.indices.bufferView
            buffer: bytes = self.access_buffer(index)
            faces = np.frombuffer(buffer, dtype=np.int32).reshape(-1, 3)
        if attr.texcoord_0 and attr.texcoord_0.bufferView:
            index = attr.texcoord_0.bufferView
            buffer: bytes = self.access_buffer(index)
            tex = np.frombuffer(buffer, dtype=np.float32).reshape(-1, 2)
        return MeshData(points, faces, tex)

    def try_finding_data(self):
        """tries to match decoded buffer data with accessor counts"""
        if self.glb.model.bufferViews is None:
            return None
        if (
            self.indices is None
            or self.attributes.position is None
            or self.attributes.texcoord_0 is None
        ):
            return None
        for index in range(len(self.glb.model.bufferViews)):
            data: bytes = self.retrieve_bufferview(index)
            # check if data is Draco compressed
            if data[:4] != b"DRAC":
                continue
            decoded = DracoPy.decode(data)
            if decoded is None:
                continue
            # compare decoded data with accessor counts
            # faces to indices
            if decoded.faces.size != self.indices.count:
                continue
            # points to positions
            if decoded.points.size != self.attributes.position.count * 3:
                continue
            # texture coordinates to texcoord_0
            if decoded.tex_coord.size != self.attributes.texcoord_0.count * 2:
                continue
            # if all checks passed, return decoded data
            return decoded
        return None

    def _get_vertex_class(self, vertex: int) -> int:
        """returns class of vertex"""
        if self.vertices_to_class[vertex] != -1:
            return self.vertices_to_class[vertex]
        if self.data is None or self.data.tex_coord is None:
            raise ValueError("No data found")
        coords = self.data.tex_coord[vertex]
        height, width = self.seg.shape
        col: int = int(coords[0] * width) % width
        row: int = int((1 - coords[1]) * height) % height
        class_id = self.seg[row][col].item()
        self.vertices_to_class[vertex] = class_id
        return class_id

    def _get_submeshes(self) -> dict[int, SubmeshSegment]:
        """returns submeshes"""
        if self.data is None:
            raise ValueError("No data found")
        if (
            self.data.points is None
            or self.data.faces is None
            or self.data.tex_coord is None
        ):
            raise ValueError("No data found")
        SubmeshSegment.points = self.data.points
        SubmeshSegment.tex_coord = self.data.tex_coord
        submeshes = defaultdict(SubmeshSegment)
        for face in tqdm(
            self.data.faces,
            desc="Loading faces",
            unit="face",
            leave=False,
        ):
            for vertex in face:
                class_id: int = self._get_vertex_class(vertex)
                submeshes[class_id].add_face(face)
        return submeshes

    def export_submeshes(self, path: Path) -> None:
        """exports submeshes"""
        for class_id, submesh in tqdm(
            self.submeshes.items(), desc="Exporting submeshes", unit="submesh"
        ):
            self.export_submesh(submesh, path / f"submesh_{class_id}.glb")

    def export_submesh(self, submesh: SubmeshSegment, path: Path) -> None:
        """exports submesh to path"""
        vertex_bytearray = bytearray()
        vertex_max: list[float] = [float("-inf")] * 3
        vertex_min: list[float] = [float("inf")] * 3
        face_bytearray = bytearray()
        tex_coord_bytearray = bytearray()
        image_bytearray: bytes = self.get_texture_image_bytes() or b""
        for vertex in submesh.vertices:
            for i, value in enumerate(vertex):
                vertex_bytearray.extend(struct.pack("f", value))
                vertex_max[i] = max(vertex_max[i], value)
                vertex_min[i] = min(vertex_min[i], value)
        for face in submesh.faces:
            for value in face:
                face_bytearray.extend(struct.pack("H", value))
        for tex_coord in submesh.uv_coords:
            for value in tex_coord:
                tex_coord_bytearray.extend(struct.pack("f", value))
        vertex_bytelen: int = len(vertex_bytearray)
        face_bytelen: int = len(face_bytearray)
        tex_coord_bytelen: int = len(tex_coord_bytearray)
        image_bytelen: int = len(image_bytearray) if image_bytearray else 0
        model = GLTFModel(
            accessors=[
                # position
                Accessor(
                    bufferView=0,
                    byteOffset=0,
                    componentType=ComponentType.FLOAT.value,
                    count=len(submesh.vertices),
                    type=AccessorType.VEC3.value,
                    max=vertex_max,
                    min=vertex_min,
                ),
                # faces
                Accessor(
                    bufferView=1,
                    byteOffset=0,
                    componentType=ComponentType.UNSIGNED_SHORT.value,
                    count=len(submesh.faces),
                    type=AccessorType.SCALAR.value,
                ),
                # tex coords
                Accessor(
                    bufferView=2,
                    byteOffset=0,
                    componentType=ComponentType.FLOAT.value,
                    count=len(submesh.uv_coords),
                    type=AccessorType.VEC2.value,
                ),
            ],
            asset=Asset(version="2.0"),
            extensionsUsed=self.glb.model.extensionsUsed,
            # scenes=[Scene(nodes=[0])],
            scenes=self.glb.model.scenes,
            nodes=self.glb.model.nodes,
            meshes=[
                Mesh(
                    primitives=[
                        Primitive(
                            attributes=Attributes(POSITION=0, TEXCOORD_0=2),
                            indices=1,
                            material=0,
                        )
                    ]
                )
            ],
            buffers=[
                Buffer(
                    byteLength=vertex_bytelen
                    + face_bytelen
                    + tex_coord_bytelen
                    + image_bytelen,
                    uri="submesh.bin",
                )
            ],
            bufferViews=[
                BufferView(
                    buffer=0,
                    byteOffset=0,
                    byteLength=vertex_bytelen,
                    target=BufferTarget.ARRAY_BUFFER.value,
                ),
                BufferView(
                    buffer=0,
                    byteOffset=vertex_bytelen,
                    byteLength=face_bytelen,
                    target=BufferTarget.ELEMENT_ARRAY_BUFFER.value,
                ),
                BufferView(
                    buffer=0,
                    byteOffset=vertex_bytelen + face_bytelen,
                    byteLength=tex_coord_bytelen,
                    target=BufferTarget.ARRAY_BUFFER.value,
                ),
                BufferView(
                    buffer=0,
                    byteOffset=vertex_bytelen
                    + face_bytelen
                    + tex_coord_bytelen,
                    byteLength=image_bytelen,
                ),
            ],
            # images=self.glb.model.images,
            images=[
                Image(
                    mimeType="image/jpeg",
                    bufferView=3,
                )
            ],
            materials=[self.material] if self.material else None,
            samplers=self.glb.model.samplers,
            textures=[Texture(sampler=0, source=0)]
            if image_bytearray
            else None,
        )
        resource = FileResource(
            "submesh.bin",
            data=vertex_bytearray
            + face_bytearray
            + tex_coord_bytearray
            + image_bytearray,
        )
        glb = GLTF(model=model, resources=[resource])
        glb.export(str(path))


class GLBSegment(BufferAccessor):
    """GLBSegment"""

    def __init__(self, path: Path) -> None:
        BufferAccessor.glb = GLTF.load(str(path))
        self.meshes: list[MeshSegment] = []

    def load_meshes(self) -> None:
        """loads meshes"""
        if self.glb.model.meshes is None:
            return
        for mesh in tqdm(
            self.glb.model.meshes,
            desc="Loading meshes",
            unit="mesh",
            leave=False,
        ):
            for primitive in tqdm(
                mesh.primitives,
                desc="Loading primitives",
                unit="primitive",
                leave=False,
            ):
                self.meshes.append(MeshSegment(primitive))

    def export_submeshes(self) -> None:
        """exports submeshes"""
        for mesh in tqdm(self.meshes, desc="Exporting mesh", unit="mesh"):
            mesh.export_submeshes(Path("."))


def main(glb_path: Path, seg_path: Path) -> None:
    """main"""
    glb = GLBSegment(glb_path)
    glb.load_meshes()
    glb.meshes[0].seg = np.load(seg_path)
    glb.export_submeshes()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Segment GLB")
    parser.add_argument(
        "-f",
        "--file",
        type=str,
        help="GLB file to segment",
        default="model.glb",
    )
    parser.add_argument(
        "-s",
        "--seg",
        type=str,
        help="Segmentation map",
        default="map.npy",
    )
    args = parser.parse_args()
    main(Path(args.file), Path(args.seg))
