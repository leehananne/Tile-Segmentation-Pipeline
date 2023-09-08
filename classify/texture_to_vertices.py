"""converts segmentation map to class for each vertex"""
import numpy as np
from trimesh import Trimesh


def get_map_value(seg: np.ndarray, coords: tuple[float, float]) -> int:
    """returns the value of the segmentation map at the given coordinates.

    (0, 0) is the top left corner of the map, (1, 1) is the bottom right corner

    parameters
    ----------
    seg: np.ndarray
        segmentation map
    coords: tuple[float, float]
        coordinates of the point to get the value of. values should be between
        0 and 1

    returns
    -------
    int
        value of the segmentation map at the given coordinates

    examples
    --------
    >>> get_map_value(np.array([[1, 2], [3, 4]]), (0, 1))
    3

    """
    height: int
    width: int
    height, width = seg.shape
    col: int = int(coords[0] * (width - 1)) % width
    row: int = int(coords[1] * (height - 1)) % height
    return seg[row][col].item()


def texture_to_vertices_trimesh(mesh: Trimesh, seg: np.ndarray) -> list[int]:
    """converts segmentation map to class for each vertex in a trimesh

    parameters
    ----------
    mesh: trimesh.Trimesh
        trimesh to convert
    seg: np.ndarray
        segmentation map

    returns
    -------
    list[int]
        list of classes for each vertex

    """
    total: int = len(mesh.vertices)
    vertices_to_class: list[int] = [-1] * total
    if mesh.visual is None:
        return vertices_to_class
    for index in range(total):
        vertices_to_class[index] = get_map_value(seg, mesh.visual.uv[index])
    return vertices_to_class


def texture_to_vertices(
    vertices: np.ndarray, tex_coords: np.ndarray, seg: np.ndarray
) -> list[int]:
    """converts segmentation map to class for each vertex

    parameters
    ----------
    vertices: np.ndarray
        vertices of the mesh
    tex_coords: np.ndarray
        texture coordinates of the mesh
    seg: np.ndarray
        segmentation map

    returns
    -------
    list[int]
        list of classes for each vertex

    """
    total: int = len(vertices)
    vertices_to_class: list[int] = [-1] * total
    for index in range(total):
        vertices_to_class[index] = get_map_value(seg, tex_coords[index])
    return vertices_to_class
