"""sort vertices by class and export submeshes"""
from collections import defaultdict
from pathlib import Path
import numpy as np
from trimesh import Trimesh, load, Scene
from tqdm import tqdm


class MeshSegment:
    """MeshSegment"""

    def __init__(self, mesh: Trimesh, index: int = 0) -> None:
        self.mesh: Trimesh = mesh
        self.index: int = index
        self.visual = mesh.visual
        self.vertices_to_class: list[int] = [-1] * len(mesh.vertices)

    @property
    def seg(self) -> np.ndarray:
        """returns segmentation map"""
        return self._seg

    @seg.setter
    def seg(self, seg: np.ndarray) -> None:
        """sets segmentation map"""
        self._seg: np.ndarray = seg
        self._height: int = seg.shape[0]
        self._width: int = seg.shape[1]

    @property
    def visual(self):
        """returns visual"""
        return self._visual

    @visual.setter
    def visual(self, visual) -> None:
        """sets visual"""
        if visual is None:
            raise ValueError("Mesh has no visual")
        self._visual = visual

    @property
    def submeshes(self) -> dict[int, Trimesh]:
        """returns submeshes"""
        if not hasattr(self, "_submeshes") or self._submeshes is None:
            self._submeshes: dict[int, Trimesh] = self._get_submeshes()
        return self._submeshes

    @submeshes.setter
    def submeshes(self, submeshes: dict[int, Trimesh]) -> None:
        """sets submeshes"""
        self._submeshes = submeshes

    def _get_vertex_class(self, vertex: int) -> int:
        """returns class of vertex"""
        if self.vertices_to_class[vertex] != -1:
            return self.vertices_to_class[vertex]
        coords = self.visual.uv[vertex]
        col: int = int(coords[0] * self._width) % self._width
        row: int = int((1 - coords[1]) * self._height) % self._height
        class_id = self.seg[row][col].item()
        self.vertices_to_class[vertex] = class_id
        return class_id

    def _get_submeshes(self) -> dict[int, Trimesh]:
        """returns a dictionary of submeshes by class"""
        if self._height == 0 or self._width == 0:
            raise ValueError("Segmentation map is empty")
        sub_faces = defaultdict(list)
        for i, face in enumerate(self.mesh.faces):
            for vertex in face:
                class_id: int = self._get_vertex_class(vertex)
                sub_faces[class_id].append(i)
        submeshes: dict[int, Trimesh] = {}
        for class_id, faces in sub_faces.items():
            submesh = self.mesh.submesh([faces], append=True)
            if not isinstance(submesh, Trimesh):
                raise ValueError("Submesh is not a Trimesh")
            submeshes[class_id] = submesh
        return submeshes

    def export_submeshes(self, path: Path) -> None:
        """exports submeshes by class"""
        submeshes: dict[int, Trimesh] = self.submeshes
        for class_id in tqdm(submeshes, desc="Exporting", unit="submesh"):
            submeshes[class_id].export(
                path / f"submesh{self.index}_{class_id}.glb"
            )


def load_glb(path: Path) -> list[MeshSegment]:
    """load glb into list of MeshSegments"""
    glb = load(path)
    if isinstance(glb, Scene):
        return [
            MeshSegment(mesh, i)
            for i, mesh in enumerate(glb.geometry.values())
        ]
    if isinstance(glb, Trimesh):
        return [MeshSegment(glb)]

    raise ValueError("Unsupported GLB type")


if __name__ == "__main__":
    # seg = torch.load("map.pt")
    seg = np.load("map.npy")
    meshes: list[MeshSegment] = load_glb(Path("model.gltf"))
    for i, mesh in enumerate(meshes):
        mesh.seg = seg
        mesh.export_submeshes(Path("output"))
