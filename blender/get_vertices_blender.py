"""sort vertices by class and export submeshes (Blender)"""
from collections import defaultdict
import bpy
import numpy as np


def get_vertex_map(obj):
    """map vertex indices to loop indices"""
    vertex_map = defaultdict(list)
    for poly in obj.data.polygons:
        for vertex_index, loop_index in zip(poly.vertices, poly.loop_indices):
            vertex_map[vertex_index].append(loop_index)
    return vertex_map


def select_vertices_by_uv(obj, seg, class_id) -> None:
    """set vertices to selected if the uv pixel is the given class"""
    width: int
    height: int
    width, height = seg.shape[1], seg.shape[0]
    for loop in obj.data.loops:
        coords = obj.data.uv_layers.active.data[loop.index].uv
        # origin is bottom left
        col: int = int(coords[0] * width) % width
        row: int = int((1 - coords[1]) * height) % height
        if seg[row][col].item() == class_id:
            obj.data.vertices[loop.vertex_index].select = True


def main() -> None:
    """main"""
    seg = np.load("C:/Users/User/Documents/dsta-stsh/map.npy")
    obj = bpy.context.object
    # deselect all vertices
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    select_vertices_by_uv(obj, seg, 2)  # 2 for buildings, 8 for vegetation
    bpy.ops.object.mode_set(mode="EDIT")
    # separate selected vertices into new object
    bpy.ops.mesh.separate(type="SELECTED")
    # bmesh.update_edit_mesh(obj.data)


if __name__ == "__main__":
    main()
