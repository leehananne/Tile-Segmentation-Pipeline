"""sort vertices by class and export submeshes. for uncompressed glTF files"""
from collections import defaultdict
from pathlib import Path
from trimesh import Trimesh, load, Scene
from tqdm import tqdm


class MeshSegment:
    """loads a trimesh and sorts vertices by class. exports submeshes by class

    parameters
    ----------
    mesh: trimesh.Trimesh
        trimesh to load and segment
    index: int
        index of the mesh

    attributes
    ----------
    mesh: trimesh.Trimesh
        trimesh to load and segment
    index: int
        index of the mesh
    vertices_to_class: list[int]
        list of classes for each vertex
    submeshes: dict[int, trimesh.Trimesh]
        dictionary of submeshes by class

    examples
    --------
    >>> meshes = MeshSegment.load_by_path(Path("model.gltf"))
    >>> for mesh in meshes:
    >>>     mesh.vertices_to_class = list_of_classes
    >>>     mesh.export_submeshes(Path("output"))

    """

    def __init__(self, mesh: Trimesh, index: int = 0) -> None:
        self.mesh: Trimesh = mesh
        """trimesh to load and segment"""

        self.index: int = index
        """index of the mesh"""

        self.vertices_to_class: list[int] = [-1] * len(mesh.vertices)
        """list of classes for each vertex"""

        self._submeshes: dict[int, Trimesh]

    @property
    def submeshes(self) -> dict[int, Trimesh]:
        """a dictionary of submeshes sorted by class

        submeshes are only generated once when this property is accessed

        returns
        -------
        dict[int, trimesh.Trimesh]
            dictionary of submeshes by class

        """
        if not hasattr(self, "_submeshes") or self._submeshes is None:
            self.load_submeshes()
        return self._submeshes

    @submeshes.setter
    def submeshes(self, submeshes: dict[int, Trimesh]) -> None:
        self._submeshes = submeshes

    @staticmethod
    def load_by_path(path: Path) -> list["MeshSegment"]:
        """loads a glb file by path and returns a list of MeshSegments

        only supports loading if glb is a Scene or Trimesh

        parameters
        ----------
        path: pathlib.Path
            path to glb file

        returns
        -------
        list[MeshSegment]
            list of MeshSegments

        """
        glb = load(path)
        if isinstance(glb, Scene):
            return [
                MeshSegment(mesh, i)
                for i, mesh in enumerate(glb.geometry.values())
            ]
        if isinstance(glb, Trimesh):
            return [MeshSegment(glb)]

        raise ValueError("Unsupported GLB type")

    def load_submeshes(self) -> None:
        """loads submeshes and saves them to the _submeshes attribute

        if vertices_to_class is changed, this method must be called again to
        update the submeshes

        """
        self._submeshes = self._get_submeshes()

    def _get_submeshes(self) -> dict[int, Trimesh]:
        """returns a dictionary of submeshes sorted by class

        avoid calling this method directly. use the submeshes property instead
        to save the submeshes to the _submeshes attribute, or use the
        _load_submeshes method to update the submeshes

        returns
        -------
        dict[int, trimesh.Trimesh]
            dictionary of submeshes by class

        """
        sub_faces = defaultdict(list)
        for i, face in enumerate(self.mesh.faces):
            for vertex_index in face:
                class_id: int = self.vertices_to_class[vertex_index]
                sub_faces[class_id].append(i)
        submeshes: dict[int, Trimesh] = {}
        for class_id, faces in sub_faces.items():
            submesh = self.mesh.submesh([faces], append=True)
            if not isinstance(submesh, Trimesh):
                raise ValueError("Submesh is not a Trimesh")
            submeshes[class_id] = submesh
        return submeshes

    def export_submeshes(self, output_dir: Path) -> None:
        """exports submeshes to the given path

        exported submeshes are saved as glb files with the following naming
        convention: submesh{`self.index`}_{`class_id`}.glb

        parameters
        ----------
        output_dir: pathlib.Path
            path of output directory to export submeshes to

        """
        submeshes: dict[int, Trimesh] = self.submeshes
        for class_id, submesh in tqdm(
            submeshes.items(), desc="Exporting", unit="submesh"
        ):
            submesh.export(output_dir / f"submesh{self.index}_{class_id}.glb")


def main() -> None:
    """main"""
    meshes: list[MeshSegment] = MeshSegment.load_by_path(Path("model.gltf"))
    for mesh in meshes:
        # ADD VERTICES TO CLASS HERE
        mesh.export_submeshes(Path("output"))


if __name__ == "__main__":
    main()
