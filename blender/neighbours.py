from collections import deque
import bpy
import bmesh
import mathutils


THRESHOLD = 1.3
UP_VECTOR = mathutils.Vector((0.0, 0.0, 1.0))
neighbours: dict = {}


def select_similar_neighbours(start_vert) -> None:
    """Selects all vertices that are similar to the given vertex."""
    if not start_vert:
        return
    start_vert.select = True
    queue = deque([start_vert])
    while queue:
        vert = queue.popleft()
        for edge in vert.link_edges:
            other = edge.other_vert(vert)
            if other.select:
                continue
            if check_similarity(vert, other):
                other.select = True
                queue.append(other)


def check_similarity(vert, other) -> bool:
    """Checks if the given vertices are similar. Two vertices are similar if
    their angle to the z-axis is within a certain threshold."""
    vector = vert.co - other.co
    angle = vector.angle(UP_VECTOR)
    if (
        vert.index not in neighbours
        or neighbours[vert.index] * THRESHOLD
        >= angle
        >= neighbours[vert.index] / THRESHOLD
    ):
        neighbours[other.index] = angle
        print(angle, neighbours.get(vert.index, 0.0), "selected")
        return True
    print(angle, neighbours.get(vert.index, 0.0), "not selected")
    return False


def main() -> None:
    """Selects all vertices that are similar to the active vertex."""
    obj = bpy.context.object
    bm = bmesh.from_edit_mesh(obj.data)
    select_similar_neighbours(bm.select_history.active)
    bm.select_flush_mode()
    bmesh.update_edit_mesh(obj.data)


if __name__ == "__main__":
    main()
