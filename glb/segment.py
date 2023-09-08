"""segment glb with draco compression"""
import struct
from collections import defaultdict
from pathlib import Path

from typing import Optional

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
    Image,
)
from gltflib import GLTFModel, Asset, Mesh
from gltflib.gltf import GLTF
from gltflib.gltf_resource import GLBResource
from tqdm import tqdm

from .decompress import PrimitiveDecompress, GLBDecompress, MeshData


class SubPrimitive:
    """a subset of a primitive

    class attributes `points` and `tex_coord` are used to store the data of the
    parent primitive.

    attributes
    ----------
    vertices: list[np.ndarray]
        list of coordinates of each vertex
    faces: list[np.ndarray]
        list of vertex indices of each face in the subprimitive
    uv_coords: list[np.ndarray]
        list of texture coordinates of each vertex
    vertex_map: dict[int, int]
        dictionary mapping parent vertex indices to subprimitive vertex indices

    examples
    --------
    >>> SubPrimitive.points = np.array([
        [0, 0, 0], [0, 0, 1], [0, 1, 0], [0, 1, 1], [1, 0, 0]
        ])
    >>> SubPrimitive.tex_coord = np.array([
        [0, 0], [1, 0], [0, 1], [1, 1], [0.5, 0.5]
        ])
    >>> subprimitive = SubPrimitive()
    >>> subprimitive.add_face(np.array([0, 2, 4]))
    >>> subprimitive.to_dict()
    {
        "vertices": np.array([
            [0, 0, 0], [0, 1, 0], [1, 0, 0]
            ]),
        "faces": np.array([
            [0, 1, 2]
            ]),
        "uv_coords": np.array([
            [0, 0], [0, 1], [0.5, 0.5]
            ])
    }

    """

    points: np.ndarray
    """points of the parent primitive"""

    tex_coord: np.ndarray
    """texture coordinates of the parent primitive"""

    def __init__(self) -> None:
        self.vertices: list[np.ndarray] = []
        """list of coordinates of each vertex"""

        self.faces: list[np.ndarray] = []
        """list of vertex indices of each face in the subprimitive"""

        self.uv_coords: list[np.ndarray] = []
        """list of texture coordinates of each vertex"""

        self.vertex_map: dict[int, int] = {}
        """dictionary mapping parent vertex indices to subprimitive vertex"""

    def add_face(self, face: np.ndarray) -> None:
        """adds a face from the parent primitive to the subprimitive

        appends vertices, faces, and texture coordinates with updated
        vertex indices for the subprimitive

        parameters
        ----------
        face: np.ndarray
            face from the parent primitive containing vertex indices

        """
        new_face: list[int] = []
        for vertex in face:
            if vertex not in self.vertex_map:
                self.vertex_map[vertex] = len(self.vertices)
                self.vertices.append(self.points[vertex])
                self.uv_coords.append(self.tex_coord[vertex])
            new_face.append(self.vertex_map[vertex])
        self.faces.append(np.array(new_face))

    def to_dict(self) -> dict[str, np.ndarray]:
        """converts to a dictionary containing numpy arrays of vertices, faces,
        and texture coordinates

        returns
        -------
        dict[str, np.ndarray]
            dictionary containing numpy arrays of vertices, faces, and texture
            coordinates

        """
        return {
            "vertices": np.array(self.vertices),
            "faces": np.array(self.faces),
            "uv_coords": np.array(self.uv_coords),
        }

    def to_mesh_data(self) -> MeshData:
        """converts to a MeshData object

        returns
        -------
        MeshData
            MeshData object containing vertices, faces, and texture coordinates

        """
        return MeshData(
            points=np.array(self.vertices),
            faces=np.array(self.faces),
            tex_coord=np.array(self.uv_coords),
        )


class PrimitiveSegment(PrimitiveDecompress):
    """loads a primitive and sorts vertices by class. exports submeshes
    by class into separate glb files

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
    vertices_to_class: list[int]
        list of classes for each vertex
    subprimitives: dict[int, SubPrimitive]
        dictionary of subprimitives sorted by class
    material: gltflib.Material or None
        material of the primitive

    examples
    --------
    >>> primitive_seg = PrimitiveSegment(primitive)
    >>> primitive_seg.vertices_to_class = list_of_classes
    >>> primitive_seg.export_subprimitives(Path("output"))

    """

    def __init__(self, primitive: Primitive) -> None:
        super().__init__(primitive)

        self.vertices_to_class: list[int] = [-1] * self.data.points.shape[0]
        """list of classes for each vertex"""

        self._subprimitives: dict[int, SubPrimitive]

    @property
    def subprimitives(self) -> dict[int, SubPrimitive]:
        """dictionary of subprimitives sorted by class

        subprimitives are only generated once when this property is accessed

        returns
        -------
        dict[int, SubPrimitive]
            dictionary of subprimitives by class

        """
        if not hasattr(self, "_subprimitives") or self._subprimitives is None:
            self.load_subprimitives()
        return self._subprimitives

    @subprimitives.setter
    def subprimitives(self, subprimitives: dict[int, SubPrimitive]) -> None:
        self._subprimitives = subprimitives

    def load_subprimitives(self) -> None:
        """loads subprimitives and saves them to the _subprimitives attribute

        if vertices_to_class is changed, this method must be called again to
        update the subprimitives

        """
        self._subprimitives = self._get_subprimitives()

    def _get_subprimitives(self) -> dict[int, SubPrimitive]:
        """returns a dictionary of subprimitives sorted by class

        avoid calling this method directly. use the subprimitves property
        instead to save the subprimitves to the subprimitves attribute, or use
        the _load_subprimitves method to update the subprimitves

        returns
        -------
        dict[int, SubPrimitive]
            dictionary of subprimitives by class

        """
        if self.data is None:
            raise ValueError("No data found")
        if (
            self.data.points.size == 0
            or self.data.faces.size == 0
            or self.data.tex_coord.size == 0
        ):
            raise ValueError("No data found")
        SubPrimitive.points = self.data.points
        SubPrimitive.tex_coord = self.data.tex_coord
        submeshes = defaultdict(SubPrimitive)
        for face in tqdm(
            self.data.faces,
            desc="Loading faces",
            unit="face",
            leave=False,
        ):
            for vertex in face:
                class_id: int = self.vertices_to_class[vertex]
                submeshes[class_id].add_face(face)
        return submeshes

    def export_subprimitives(self, path: Path) -> None:
        """exports subprimitives by class to the given path

        exported subprimitives are saved as glb files with the following naming
        convention: {`path`}/class_{`class_id`}.glb

        parameters
        ----------
        path: pathlib.Path
            path to export subprimitives to

        """
        Path.mkdir(path, parents=True, exist_ok=True)
        for class_id, subprimitive in tqdm(
            self.subprimitives.items(), desc="Exporting", unit="subprimitive"
        ):
            self.export_subprimitive(
                subprimitive, path / f"class_{class_id}.glb"
            )

    def export_subprimitive(
        self, subprimitive: SubPrimitive, path: Path
    ) -> None:
        """exports subprimitive to the given path

        path should specify the entire path including the file name and
        extension (e.g. "output/subprimitive.glb")

        parameters
        ----------
        subprimitive: SubPrimitive
            subprimitive to export
        path: pathlib.Path
            path to export subprimitive to

        """
        vertex_bytearray = bytearray()
        vertex_max: list[float] = [float("-inf")] * 3
        vertex_min: list[float] = [float("inf")] * 3
        face_bytearray = bytearray()
        tex_coord_bytearray = bytearray()
        # image_bytearray: bytes = self.get_texture_image_bytes() or b""
        for vertex in subprimitive.vertices:
            for i, value in enumerate(vertex):
                vertex_bytearray.extend(struct.pack("f", value))
                vertex_max[i] = max(vertex_max[i], value)
                vertex_min[i] = min(vertex_min[i], value)
        for face in subprimitive.faces:
            for value in face:
                face_bytearray.extend(struct.pack("H", value))
        for tex_coord in subprimitive.uv_coords:
            for value in tex_coord:
                tex_coord_bytearray.extend(struct.pack("f", value))
        vertex_bytelen: int = len(vertex_bytearray)
        face_bytelen: int = len(face_bytearray)
        tex_coord_bytelen: int = len(tex_coord_bytearray)
        # image_bytelen: int = len(image_bytearray) if image_bytearray else 0
        model = GLTFModel(
            accessors=[
                # position
                Accessor(
                    bufferView=0,
                    byteOffset=0,
                    componentType=ComponentType.FLOAT.value,
                    count=len(subprimitive.vertices),
                    type=AccessorType.VEC3.value,
                    max=vertex_max,
                    min=vertex_min,
                ),
                # faces
                Accessor(
                    bufferView=1,
                    byteOffset=0,
                    componentType=ComponentType.UNSIGNED_SHORT.value,
                    count=len(subprimitive.faces) * 3,
                    type=AccessorType.SCALAR.value,
                ),
                # tex coords
                Accessor(
                    bufferView=2,
                    byteOffset=0,
                    componentType=ComponentType.FLOAT.value,
                    count=len(subprimitive.uv_coords),
                    type=AccessorType.VEC2.value,
                ),
            ],
            asset=Asset(version="2.0"),
            extensionsUsed=self.glb.model.extensionsUsed,
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
            ],
            materials=[self.material] if self.material else None,
            samplers=self.glb.model.samplers,
            textures=self.glb.model.textures,
        )
        image_bytearray: bytes = bytearray()
        for image in self.glb.model.images or []:
            bufferview: Optional[int] = image.bufferView
            if bufferview is None:
                continue
            image_bytes = self.retrieve_bufferview(bufferview)
            if model.images is None:
                model.images = []
            model.images.append(
                Image(
                    mimeType=image.mimeType,
                    bufferView=len(model.bufferViews or []),
                )
            )
            if model.bufferViews is None:
                model.bufferViews = []
            model.bufferViews.append(
                BufferView(
                    buffer=0,
                    byteOffset=vertex_bytelen
                    + face_bytelen
                    + tex_coord_bytelen
                    + len(image_bytearray),
                    byteLength=len(image_bytes),
                )
            )
            image_bytearray.extend(image_bytes)

        model.buffers = [
            Buffer(
                byteLength=vertex_bytelen
                + face_bytelen
                + tex_coord_bytelen
                + len(image_bytearray),
            )
        ]

        resource = GLBResource(
            data=vertex_bytearray
            + face_bytearray
            + tex_coord_bytearray
            + image_bytearray,
        )

        GLTF(model=model, resources=[resource]).export(str(path))


class GLBSegment(GLBDecompress):
    """loads a glb and loads primitives of each mesh. exports a glb with
    metadata from each PrimitiveSegment

    class attribute `glb` is used to store the glTF object to access

    parameters
    ----------
    path: pathlib.Path
        path to glb file

    attributes
    ----------
    glb: gltflib.GLTF
        the glTF object to access and segment
    meshes: list[list[PrimitiveSegment]]
        list of meshes containing lists of primitives

    examples
    --------
    >>> glb = GLBSegment(Path("model.glb"))
    >>> glb.load_meshes()
    >>> glb.export(Path("output/model.glb"))
    >>> glb.export_submeshes(Path("output"))

    """

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.meshes: list[list[PrimitiveSegment]] = []
        """list of meshes containing lists of primitives"""

    def load_meshes(self) -> None:
        """loads meshes and primitives from the glb and saves the loaded
        PrimitiveSegs to the meshes attribute

        running this method twice will result in duplicate PrimitiveSegs in the
        meshes attribute, so set the meshes attribute to an empty list before
        calling this method again

        """
        if self.glb.model.meshes is None:
            return
        for mesh in tqdm(
            self.glb.model.meshes,
            desc="Loading meshes",
            unit="mesh",
            leave=False,
        ):
            primitives: list[PrimitiveSegment] = []
            for primitive in tqdm(
                mesh.primitives,
                desc="Loading primitives",
                unit="primitive",
                leave=False,
            ):
                primitives.append(PrimitiveSegment(primitive))
            self.meshes.append(primitives)

    def export(self, path: Path) -> None:
        """exports the glb with metadata from each PrimitiveSegment to the
        given path

        the path should specify the entire path including the file name and
        extension (e.g. "output/model.glb")

        parameters
        ----------
        path: pathlib.Path
            path to export the glb to

        """
        if self.glb.model.meshes is None:
            return
        if self.glb.model.buffers is None:
            self.glb.model.buffers = []
        if self.glb.model.bufferViews is None:
            self.glb.model.bufferViews = []
        if self.glb.model.accessors is None:
            self.glb.model.accessors = []
        if self.glb.model.extensionsUsed is None:
            self.glb.model.extensionsUsed = []
        for mesh in tqdm(
            self.meshes,
            desc="Exporting mesh",
            unit="mesh",
            leave=False,
        ):
            for primitive_seg in mesh:
                primitive: Primitive = primitive_seg.primitive
                feature_bytearray = bytearray()
                for vertex in primitive_seg.vertices_to_class:
                    feature_bytearray.extend(struct.pack("f", vertex))
                feature_bytelen: int = len(feature_bytearray)
                if primitive.extensions is None:
                    primitive.extensions = {}
                primitive.extensions["EXT_mesh_features"] = {
                    "featureIds": [
                        {
                            "featureCount": len(
                                set(primitive_seg.vertices_to_class)
                            ),
                            "attribute": 0,
                        }
                    ]
                }
                # TO DO: FIX THIS
                # THIS REQUIRES ADDING _FEATURE_ID_0 TO THE ATTRIBUTES CLASS
                primitive.attributes._FEATURE_ID_0 = len(
                    self.glb.model.accessors
                )
                self.glb.model.accessors.append(
                    Accessor(
                        bufferView=len(self.glb.model.bufferViews),
                        byteOffset=0,
                        componentType=ComponentType.FLOAT.value,
                        count=primitive_seg.data.points.shape[0],
                        type=AccessorType.SCALAR.value,
                        normalized=False,
                    )
                )
                self.glb.model.bufferViews.append(
                    BufferView(
                        buffer=0,
                        byteOffset=len(self.glb.get_glb_resource().data),
                        byteLength=feature_bytelen,
                        byteStride=4,
                        target=BufferTarget.ARRAY_BUFFER.value,
                    )
                )
                self.glb.model.buffers[0].byteLength += feature_bytelen
                self.glb.glb_resources[0].data += feature_bytearray
        self.glb.model.extensionsUsed.append("EXT_mesh_features")
        Path.mkdir(path.parent, parents=True, exist_ok=True)
        self.glb.export(str(path))

    def export_submeshes(self, output_dir: Path) -> None:
        """exports submeshes by class to the given path

        exported submeshes are saved as glb files with the following naming
        convention: {`output_dir`}/mesh_{`mesh_index`}/class_{`class_id`}.glb

        parameters
        ----------
        output_dir: pathlib.Path
            path to export submeshes to

        """
        for i, mesh in enumerate(self.meshes):
            for j, primitive_seg in enumerate(
                tqdm(
                    mesh,
                    desc="Exporting mesh",
                    unit="mesh",
                    leave=False,
                )
            ):
                primitive_seg.export_subprimitives(output_dir / f"mesh{i}/{j}")
