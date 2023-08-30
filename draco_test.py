"""low level draco test"""
import operator
import struct
from collections import defaultdict
from pathlib import Path

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
    GLTFModel,
    Mesh,
    Primitive,
    Image,
)
from gltflib.gltf_resource import FileResource
from gltflib.gltf import GLTF

# from PIL.Image import Image

from extract_textures import get_gltf_image_data


class SubmeshSegment:
    """SubmeshSegment"""

    points: list[np.ndarray]
    tex_coord: list[np.ndarray]

    def __init__(self) -> None:
        self.vertices: list[np.ndarray] = []
        self.faces: list[np.ndarray] = []
        self.uv_coords: list[np.ndarray] = []
        self.vertex_map: dict[int, int] = {}

    def add_face(self, face: np.ndarray) -> None:
        """adds face"""
        new_face = []
        for vertex in face:
            if vertex not in self.vertex_map:
                self.vertex_map[vertex] = len(self.vertices)
                self.vertices.append(self.points[vertex])
                self.uv_coords.append(self.tex_coord[vertex])
            new_face.append(self.vertex_map[vertex])
        self.faces.append(np.array(new_face))

    def to_dict(self) -> dict[str, list[np.ndarray]]:
        """returns dict"""
        return {
            "vertices": self.vertices,
            "faces": self.faces,
            "uv_coords": self.uv_coords,
        }


class MeshSegment:
    """MeshSegment"""

    def __init__(self, path: Path):
        self.glb = GLTF.load(str(path))
        self.seg: np.ndarray = np.array([])
        self.vertices_to_class: list[int] = [-1] * len(self._data.points)

    @property
    def glb(self) -> GLTF:
        """returns glb"""
        return self._glb

    @glb.setter
    def glb(self, glb: GLTF) -> None:
        """sets glb"""
        self._glb: GLTF = glb
        self._data = DracoPy.decode(glb.resources[0].data)

    @property
    def submeshes(self) -> dict[int, SubmeshSegment]:
        """returns submeshes"""
        if not hasattr(self, "_submeshes") or self._submeshes is None:
            self._submeshes: dict[int, SubmeshSegment] = self._get_submeshes()
        return self._submeshes

    @submeshes.setter
    def submeshes(self, submeshes: dict[int, SubmeshSegment]) -> None:
        """sets subvertices"""
        self._submeshes = submeshes

    def _get_vertex_class(self, vertex: int) -> int:
        """returns class of vertex"""
        if self.vertices_to_class[vertex] != -1:
            return self.vertices_to_class[vertex]
        coords = self._data.tex_coord[vertex]
        height, width = self.seg.shape
        col: int = int(coords[0] * width) % width
        row: int = int((1 - coords[1]) * height) % height
        class_id = self.seg[row][col].item()
        self.vertices_to_class[vertex] = class_id
        return class_id

    def _get_subvertices(self) -> defaultdict[int, list[np.ndarray]]:
        """returns subvertices"""
        sub_vertices = defaultdict(list)
        for face in self._data.faces:
            for vertex in face:
                class_id: int = self._get_vertex_class(vertex)
                sub_vertices[class_id].append(self._data.points[vertex])
        return sub_vertices

    def _get_submeshes(self) -> dict[int, SubmeshSegment]:
        """returns submeshes"""
        SubmeshSegment.points = self._data.points
        SubmeshSegment.tex_coord = self._data.tex_coord
        submeshes = defaultdict(SubmeshSegment)
        for face in self._data.faces:
            for vertex in face:
                class_id: int = self._get_vertex_class(vertex)
                submeshes[class_id].add_face(face)
        return submeshes

    def export_vertices(self, vertices: list[np.ndarray], path: Path) -> None:
        """exports vertices to path"""
        vertex_bytearray = bytearray()
        for vertex in vertices:
            for value in vertex:
                vertex_bytearray.extend(struct.pack("f", value))
        bytelen = len(vertex_bytearray)
        mins = [
            min(operator.itemgetter(i)(vertex) for vertex in vertices)
            for i in range(3)
        ]
        maxs = [
            max(operator.itemgetter(i)(vertex) for vertex in vertices)
            for i in range(3)
        ]
        model = GLTFModel(
            accessors=[
                Accessor(
                    bufferView=0,
                    byteOffset=0,
                    componentType=ComponentType.FLOAT.value,
                    count=len(vertices),
                    type=AccessorType.VEC3.value,
                    min=mins,
                    max=maxs,
                )
            ],
            # asset=Asset(version="2.0"),
            asset=self.glb.model.asset,
            # scenes=[Scene(nodes=[0])],
            scenes=self.glb.model.scenes,
            # nodes=[Node(mesh=0)],
            nodes=self.glb.model.nodes,
            meshes=[
                Mesh(primitives=[Primitive(attributes=Attributes(POSITION=0))])
            ],
            buffers=[Buffer(byteLength=bytelen, uri="vertices.bin")],
            bufferViews=[
                BufferView(
                    buffer=0,
                    byteOffset=0,
                    byteLength=bytelen,
                    target=BufferTarget.ARRAY_BUFFER.value,
                )
            ],
            images=self.glb.model.images,
            textures=self.glb.model.textures,
        )
        resource = FileResource("vertices.bin", data=vertex_bytearray)
        glb = GLTF(model=model, resources=[resource])
        glb.export(str(path))

    def export_submesh(self, submesh: SubmeshSegment, path: Path) -> None:
        """exports submesh to path"""
        vertex_bytearray = bytearray()
        face_bytearray = bytearray()
        tex_coord_bytearray = bytearray()
        images_bytearray = bytearray()
        images_bytelens = []
        for vertex in submesh.vertices:
            for value in vertex:
                vertex_bytearray.extend(struct.pack("f", value))
        for face in submesh.faces:
            for value in face:
                face_bytearray.extend(struct.pack("H", value))
        for tex_coord in submesh.uv_coords:
            for value in tex_coord:
                tex_coord_bytearray.extend(struct.pack("f", value))
        for image in self.glb.model.images or []:
            data = get_gltf_image_data(self.glb, image)
            images_bytearray.extend(data)
            images_bytelens.append(len(data))
        vertex_bytelen = len(vertex_bytearray)
        face_bytelen = len(face_bytearray)
        tex_coord_bytelen = len(tex_coord_bytearray)
        model = GLTFModel(
            accessors=[
                Accessor(
                    bufferView=0,
                    byteOffset=0,
                    componentType=ComponentType.FLOAT.value,
                    count=len(submesh.vertices),
                    type=AccessorType.VEC3.value,
                ),
                Accessor(
                    bufferView=1,
                    byteOffset=0,
                    componentType=ComponentType.UNSIGNED_SHORT.value,
                    count=len(submesh.faces),
                    type=AccessorType.SCALAR.value,
                ),
                Accessor(
                    bufferView=2,
                    byteOffset=0,
                    componentType=ComponentType.FLOAT.value,
                    count=len(submesh.uv_coords),
                    type=AccessorType.VEC2.value,
                ),
            ],
            # asset=Asset(version="2.0"),
            asset=self.glb.model.asset,
            extensionsUsed=self.glb.model.extensionsUsed,
            # scenes=[Scene(nodes=[0])],
            scenes=self.glb.model.scenes,
            # nodes=[Node(mesh=0)],
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
                    + sum(images_bytelens),
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
            ]
            + [
                BufferView(
                    buffer=0,
                    byteOffset=vertex_bytelen
                    + face_bytelen
                    + tex_coord_bytelen
                    + sum(images_bytelens[:i]),
                    byteLength=images_bytelens[i],
                )
                for i in range(len(images_bytelens))
            ],
            # images=self.glb.model.images,
            images=[
                Image(
                    mimeType="image/jpeg",
                    bufferView=3 + i,
                )
                for i in range(len(images_bytelens))
            ],
            materials=self.glb.model.materials,
            samplers=self.glb.model.samplers,
            textures=self.glb.model.textures,
        )
        resource = FileResource(
            "submesh.bin",
            data=vertex_bytearray
            + face_bytearray
            + tex_coord_bytearray
            + images_bytearray,
        )
        glb = GLTF(model=model, resources=[resource])
        glb.export(str(path))


def main():
    """main"""
    mesh = MeshSegment(Path("model.glb"))
    # textures: list[Image] = glb_to_pillow(mesh.glb)
    mesh.seg = np.load("map.npy")
    # for class_id, subvertices in mesh.subvertices.items():
    #     mesh.export_vertices(subvertices, Path(f"vertices_{class_id}.glb"))
    for class_id, submesh in mesh.submeshes.items():
        print(class_id)
        mesh.export_submesh(submesh, Path(f"output/submesh_{class_id}.glb"))


if __name__ == "__main__":
    main()
