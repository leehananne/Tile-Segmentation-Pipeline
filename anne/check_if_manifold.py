import open3d as o3d

def is_mesh_manifold(mesh):
    return o3d.geometry.TriangleMesh.is_edge_manifold(mesh)

def is_vertex_manifold(mesh):
    return o3d.geometry.TriangleMesh.is_vertex_manifold(mesh)

if __name__ == "__main__":
    # Load the .ply file
    ply_path = "python_files\singapore_4.ply"
    # Load your mesh from a file or create it
    mesh = o3d.io.read_triangle_mesh(ply_path)

    # Check if the mesh is manifold
    if is_mesh_manifold(mesh) and is_vertex_manifold(mesh):
        print("The mesh is manifold.")
    else:
        print("The mesh is not manifold.")