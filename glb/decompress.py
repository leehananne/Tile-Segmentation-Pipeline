"""segment glb with draco compression"""
import argparse
import io
import struct
from dataclasses import dataclass
from pathlib import Path

from typing import Optional, Union

import DracoPy
import numpy as np
from gltflib import (
    Accessor,
    AccessorType,
    Attributes,
    Buffer,
    BufferTarget,
    BufferView,
    ComponentType,
    Primitive,
    Material,
    Image,
    Texture,
)
from gltflib.gltf import GLTF
from gltflib.gltf_resource import GLTFResource, GLBResource, FileResource
from PIL import Image as PIL_Image
from tqdm import tqdm


@dataclass
class MeshData:
    """dataclass storing mesh data

    parameters
    ----------
    points: np.ndarray
        array containing the x, y, and z coordinates of each point
    faces: np.ndarray
        array containing the vertex indices of each face
    tex_coord: np.ndarray
        array containing the u and v coordinates of each texture coordinate

    attributes
    ----------
    points: np.ndarray
        array containing the x, y, and z coordinates of each point
    faces: np.ndarray
        array containing the vertex indices of each face
    tex_coord: np.ndarray
        array containing the u and v coordinates of each texture coordinate

    """

    points: np.ndarray
    """array containing the x, y, and z coordinates of each point"""

    faces: np.ndarray
    """array containing the vertex indices of each face"""

    tex_coord: np.ndarray
    """array containing the u and v coordinates of each texture coordinate"""

    def all(self) -> bool:
        """checks if all data is present

        returns
        -------
        bool
            True if all data is present, False otherwise

        """
        return all(
            [
                self.points.size > 0,
                self.faces.size > 0,
                self.tex_coord.size > 0,
            ]
        )


class BufferAccessor:
    """accesses buffer data contained in a glb

    attributes
    ----------
    glb: gltflib.GLTF
        the glTF object to access

    examples
    --------
    >>> BufferAccessor.glb = GLTF.load("model.glb")
    >>> BufferAccessor.get_accessor(0)
    Accessor(...)
    >>> BufferAccessor.retrieve_bufferview(0)
    b"..."
    >>> BufferAccessor.access_buffer(0)
    b"..."

    """

    glb: GLTF
    """the glTF object to access"""

    def get_accessor(
        self, accessor_index: Optional[int]
    ) -> Optional[Accessor]:
        """retrieve the accessor by accessor index

        parameters
        ----------
        accessor_index: int or None
            index of the accessor

        returns
        -------
        gltflib.Accessor or None
            accessor in the glTF if found, None otherwise

        """
        if accessor_index is None:
            return None
        return self._get_accessor(accessor_index)

    def _get_accessor(self, accessor_index: int) -> Accessor:
        """retrieve the accessor by accessor index

        parameters
        ----------
        accessor_index: int
            index of the accessor

        returns
        -------
        Accessor
            accessor in the glTF

        raises
        ------
        ValueError
            if no accessors are found
        ValueError
            if accessor index is out of range

        """
        accessors: Optional[list[Accessor]] = self.glb.model.accessors
        if accessors is None:
            raise ValueError("No accessors found")
        if accessor_index >= len(accessors):
            raise ValueError("Accessor index out of range")
        return accessors[accessor_index]

    def get_buffer_data(self, buffer: Buffer) -> bytes:
        """retrieve the data from a buffer

        parameters
        ----------
        buffer: gltflib.Buffer
            buffer to retrieve data from

        returns
        -------
        bytes
            data of the buffer

        """
        resource: Union[GLBResource, GLTFResource] = (
            self.glb.get_glb_resource()
            if buffer.uri is None
            else self.glb.get_resource(buffer.uri)
        )
        if isinstance(resource, FileResource):
            resource.load()
        return resource.data

    def retrieve_bufferview(self, buffer_view_index: int) -> bytes:
        """retrieve the data from a buffer referenced from a buffer view by
        index of the buffer view in the glTF

        parameters
        ----------
        buffer_view_index: int
            index of the buffer view in the glTF

        returns
        -------
        bytes
            data of the buffer referenced from the buffer view
        """
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
        """retrieve the data from a buffer referenced from an accessor by
        index of the accessor in the glTF

        parameters
        ----------
        accessor_index: int or None
            index of the accessor in the glTF

        returns
        -------
        bytes
            data of the buffer referenced from the accessor

        """
        if accessor_index is None:
            return b""
        accessor: Accessor = self._get_accessor(accessor_index)
        if accessor.bufferView is None:
            raise ValueError("No buffer view found")
        return self.retrieve_bufferview(accessor.bufferView)


class _Attributes(BufferAccessor):
    """Attributes of a primitive, containing accessors to the data

    attributes
    ----------
    attributes: gltflib.Attributes
        the raw attributes object containing the accessor indices
    position: gltflib.Accessor or None
        accessor to the position data
    normal: gltflib.Accessor or None
        accessor to the normal data
    tangent: gltflib.Accessor or None
        accessor to the tangent data
    texcoord_0: gltflib.Accessor or None
        accessor to the texture coordinate 0 data
    texcoord_1: gltflib.Accessor or None
        accessor to the texture coordinate 1 data
    color_0: gltflib.Accessor or None
        accessor to the color data
    joints_0: gltflib.Accessor or None
        accessor to the joint data
    weights_0: gltflib.Accessor or None
        accessor to the weight data

    """

    def __init__(self, attributes: Attributes) -> None:
        self.attributes: Attributes = attributes
        """the raw attributes object containing the accessor indices"""

    @property
    def position(self) -> Optional[Accessor]:
        """retrieve the position data accessor

        returns
        -------
        gltflib.Accessor or None
            accessor to the position data if found, None otherwise

        """
        return self.get_accessor(self.attributes.POSITION)

    @property
    def normal(self) -> Optional[Accessor]:
        """retrieve the normal data accessor

        returns
        -------
        gltflib.Accessor or None
            accessor to the normal data if found, None otherwise
        """
        return self.get_accessor(self.attributes.NORMAL)

    @property
    def tangent(self) -> Optional[Accessor]:
        """retrieve the tangent data accessor

        returns
        -------
        gltflib.Accessor or None
            accessor to the tangent data if found, None otherwise
        """
        return self.get_accessor(self.attributes.TANGENT)

    @property
    def texcoord_0(self) -> Optional[Accessor]:
        """retrieve the texture coordinate 0 data accessor

        returns
        -------
        gltflib.Accessor or None
            accessor to the texture coordinate 0 data if found, None otherwise

        """
        return self.get_accessor(self.attributes.TEXCOORD_0)

    @property
    def texcoord_1(self) -> Optional[Accessor]:
        """retrieve the texture coordinate 1 data accessor

        returns
        -------
        gltflib.Accessor or None
            accessor to the texture coordinate 1 data if found, None otherwise
        """
        return self.get_accessor(self.attributes.TEXCOORD_1)

    @property
    def color_0(self) -> Optional[Accessor]:
        """retrieve the color data accessor

        returns
        -------
        gltflib.Accessor or None
            accessor to the color data if found, None otherwise

        """
        return self.get_accessor(self.attributes.COLOR_0)

    @property
    def joints_0(self) -> Optional[Accessor]:
        """retrieve the joints data accessor

        returns
        -------
        gltflib.Accessor or None
            accessor to the joint data if found, None otherwise

        """
        return self.get_accessor(self.attributes.JOINTS_0)

    @property
    def weights_0(self) -> Optional[Accessor]:
        """retrieve the weights data accessor

        returns
        -------
        gltflib.Accessor or None
            accessor to the weight data if found, None otherwise

        """
        return self.get_accessor(self.attributes.WEIGHTS_0)


class PrimitiveDecompress(BufferAccessor):
    """loads a primitive and decompresses Draco compression if found

    parameters
    ----------
    primitive: gltflib.Primitive
        primitive to load and segment

    attributes
    ----------
    primitive: gltflib.Primitive
        primitive to load and segment
    attributes: _Attributes
        attributes of the primitive containing accessors to the data
    indices: gltflib.Accessor or None
        accessor to the indices data
    data: MeshData
        data of the primitive containing vertices, faces,
        and texture coordinates
    material: gltflib.Material or None
        material of the primitive

    examples
    --------
    >>> primitive_decompressed = PrimitiveDecompress(primitive)

    """

    def __init__(self, primitive: Primitive) -> None:
        self.primitive: Primitive = primitive
        """primitive to load and segment"""

        self.attributes: _Attributes = _Attributes(primitive.attributes)
        """attributes of the primitive containing accessors to the data"""

        self.indices: Optional[Accessor] = self.get_accessor(primitive.indices)
        """accessor to the indices data"""

        self.data: MeshData = self._get_data()
        """data of the primitive containing vertices, faces, and texture
        coordinates"""

        self._material: Optional[Material]

    @property
    def material(self) -> Optional[Material]:
        """material of the primitive if found

        returns
        -------
        gltflib.Material or None
            material of the primitive if found, None otherwise

        """
        if not hasattr(self, "_material"):
            self._material = self.get_material(self.primitive.material)
        return self._material

    def get_material(
        self, material_index: Optional[int]
    ) -> Optional[Material]:
        """retrieve the material in the glTF by index

        parameters
        ----------
        material_index: int or None
            index of the material in the glTF

        returns
        -------
        gltflib.Material or None
            material in the glTF if found, None otherwise

        """
        if material_index is None:
            return None
        materials: Optional[list[Material]] = self.glb.model.materials
        if materials is None:
            raise ValueError("No materials found")
        if material_index >= len(materials):
            raise ValueError("Material index out of range")
        return materials[material_index]

    def get_texture_image_bytes(self) -> Optional[bytes]:
        """retrieve the bytes data of the texture image from self.material

        self.material should be set before calling this method. uses
        pbrMetallicRoughness.baseColorTexture.index to retrieve the texture

        returns
        -------
        bytes or None
            bytes data of the texture image if found, None otherwise

        """
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
        """retrieve the texture image from self.material

        self.material should be set before calling this method. uses
        pbrMetallicRoughness.baseColorTexture.index to retrieve the texture

        returns
        -------
        PIL.Image.Image or None
            texture image if found, None otherwise

        """
        data: Optional[bytes] = self.get_texture_image_bytes()
        if data is None:
            return None
        return PIL_Image.open(io.BytesIO(data))

    def _get_data(self) -> MeshData:
        """attempts to retrieve data from attributes accessors and Draco
        compression

        tries to retrieve data from attributes accessors first. if no data is
        found, tries to retrieve data from Draco compression. if no data is
        found, raises ValueError

        returns
        -------
        MeshData
            data of the primitive containing vertices, faces,
            and texture coordinates

        """
        data: MeshData = self.retrieve_data()
        if data.all():
            return data
        try_data = self.try_finding_data()
        if try_data:
            return try_data
        raise ValueError("No data found")

    def retrieve_data(self) -> MeshData:
        """retrieves data from attributes accessors and indices accessor

        tries to retrieve data from accessors. if no data is found, returns
        empty arrays for points, faces, and texture coordinates in MeshData

        returns
        -------
        MeshData
            data of the primitive containing vertices, faces,
            and texture coordinates

        """
        points: np.ndarray = np.array([])  # vec3 float
        faces: np.ndarray = np.array([])  # vec3 int
        tex: np.ndarray = np.array([])  # vec2 float
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
        """tries to find data from Draco decompression and matches the data
        with the counts of each property from the accessors

        returns
        -------
        MeshData or None
            data of the primitive containing vertices, faces,
            and texture coordinates if found, None otherwise

        """
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


class GLBDecompress(BufferAccessor):
    """loads a glb and loads primitives from the glb to decompress

    class attribute `glb` is used to store the glTF object to access

    parameters
    ----------
    path: pathlib.Path
        path to glb file

    attributes
    ----------
    glb: gltflib.GLTF
        the glTF object to access and decompress
    meshes: list[list[PrimitiveDecompress]]
        list of meshes containing lists of primitives

    examples
    --------
    >>> glb = GLBDecompress(Path("model.glb"))
    >>> glb.load_meshes()
    >>> glb.export(Path("output/model.glb"))

    """

    def __init__(self, path: Path) -> None:
        BufferAccessor.glb = GLTF.load(str(path))
        self.meshes: list[list[PrimitiveDecompress]] = []
        """list of meshes containing lists of primitives"""

    def load_meshes(self) -> None:
        """loads meshes and primitives from the glb and saves the loaded
        PrimitiveDecompress to the meshes attribute

        running this method twice will result in duplicate PrimitiveDecompress
        in the meshes attribute, so set the meshes attribute to an empty list
        before calling this method again

        """
        if self.glb.model.meshes is None:
            return
        for mesh in tqdm(
            self.glb.model.meshes,
            desc="Loading meshes",
            unit="mesh",
            leave=False,
        ):
            primitives: list[PrimitiveDecompress] = []
            for primitive in tqdm(
                mesh.primitives,
                desc="Loading primitives",
                unit="primitive",
                leave=False,
            ):
                primitives.append(PrimitiveDecompress(primitive))
            self.meshes.append(primitives)

    def export(self, path: Path) -> None:
        """exports the decompressed glb to the specified path

        the path should specify the entire path including the file name and
        extension (e.g. "output/model.glb")

        parameters
        ----------
        path: pathlib.Path
            path to export the glb to

        """
        glb: GLTF = self.glb.clone()
        if glb.model.meshes is None:
            return
        data = bytearray()
        accessors: list[Accessor] = []
        bufferviews: list[BufferView] = []
        for i, mesh in enumerate(self.meshes):
            for j, primitive in enumerate(mesh):
                _primitive: Primitive = glb.model.meshes[i].primitives[j]
                _primitive.extensions = None
                vertex_bytearray = bytearray()
                vertex_max: list[float] = [float("-inf")] * 3
                vertex_min: list[float] = [float("inf")] * 3
                face_bytearray = bytearray()
                tex_coord_bytearray = bytearray()
                for vertex in primitive.data.points:
                    for k, value in enumerate(vertex):
                        vertex_bytearray.extend(struct.pack("f", value))
                        vertex_max[k] = max(vertex_max[k], value)
                        vertex_min[k] = min(vertex_min[k], value)
                for face in primitive.data.faces:
                    for value in face:
                        face_bytearray.extend(struct.pack("H", value))
                # pad faces to multiple of 4 bytes
                face_bytearray.extend(b"\x00" * (len(face_bytearray) % 4))
                for tex_coord in primitive.data.tex_coord:
                    for value in tex_coord:
                        tex_coord_bytearray.extend(struct.pack("f", value))
                vertex_bytelen: int = len(vertex_bytearray)
                face_bytelen: int = len(face_bytearray)
                tex_coord_bytelen: int = len(tex_coord_bytearray)

                _primitive.indices = len(accessors)
                accessors.append(
                    # face accessor
                    Accessor(
                        bufferView=len(bufferviews),
                        byteOffset=0,
                        componentType=ComponentType.UNSIGNED_SHORT,
                        count=len(primitive.data.faces) * 3,
                        type=AccessorType.SCALAR.value,
                    )
                )
                bufferviews.append(
                    # face buffer view
                    BufferView(
                        buffer=0,
                        byteOffset=len(data),
                        byteLength=face_bytelen,
                        target=BufferTarget.ELEMENT_ARRAY_BUFFER.value,
                    )
                )
                data.extend(face_bytearray)

                _primitive.attributes.POSITION = len(accessors)
                accessors.append(
                    # vertex accessor
                    Accessor(
                        bufferView=len(bufferviews),
                        byteOffset=0,
                        componentType=ComponentType.FLOAT,
                        count=len(primitive.data.points),
                        type=AccessorType.VEC3.value,
                        min=vertex_min,
                        max=vertex_max,
                    )
                )
                bufferviews.append(
                    # vertex buffer view
                    BufferView(
                        buffer=0,
                        byteOffset=len(data),
                        byteLength=vertex_bytelen,
                        target=BufferTarget.ARRAY_BUFFER.value,
                    )
                )
                data.extend(vertex_bytearray)

                _primitive.attributes.TEXCOORD_0 = len(accessors)
                accessors.append(
                    # tex coord accessor
                    Accessor(
                        bufferView=len(bufferviews),
                        byteOffset=0,
                        componentType=ComponentType.FLOAT,
                        count=len(primitive.data.tex_coord),
                        type=AccessorType.VEC2.value,
                    )
                )
                bufferviews.append(
                    # tex coord buffer view
                    BufferView(
                        buffer=0,
                        byteOffset=len(data),
                        byteLength=tex_coord_bytelen,
                        target=BufferTarget.ARRAY_BUFFER.value,
                    )
                )
                data.extend(tex_coord_bytearray)

        if glb.model.images:
            for image in glb.model.images:
                if self.glb.model.bufferViews is None:
                    continue
                if image.bufferView is None:
                    continue
                old_index: int = image.bufferView
                bufferview: BufferView = self.glb.model.bufferViews[old_index]
                image.bufferView = len(bufferviews)
                bufferviews.append(
                    BufferView(
                        buffer=0,
                        byteOffset=len(data),
                        byteLength=bufferview.byteLength,
                    )
                )
                data.extend(self.retrieve_bufferview(old_index))

        buffers: list[Buffer] = [
            Buffer(
                byteLength=len(data),
                uri=None,
            )
        ]

        resource = GLBResource(data=data)
        glb.resources.clear()
        glb.resources.append(resource)
        glb.model.buffers = buffers
        glb.model.bufferViews = bufferviews
        glb.model.accessors = accessors
        if (
            glb.model.extensionsUsed is not None
            and "KHR_draco_mesh_compression" in glb.model.extensionsUsed
        ):
            glb.model.extensionsUsed.remove("KHR_draco_mesh_compression")
        if (
            glb.model.extensionsRequired is not None
            and "KHR_draco_mesh_compression" in glb.model.extensionsRequired
        ):
            glb.model.extensionsRequired.remove("KHR_draco_mesh_compression")

        Path.mkdir(path.parent, parents=True, exist_ok=True)
        glb.export(str(path))


def main(glb_path: Path, output_dir: Path) -> None:
    """main"""
    glb = GLBDecompress(glb_path)
    glb.load_meshes()
    glb.export(output_dir / glb_path.name)


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
        "-o",
        "--output-dir",
        type=str,
        help="Output directory",
        default="output",
    )
    args: argparse.Namespace = parser.parse_args()
    main(Path(args.file), Path(args.output_dir))
