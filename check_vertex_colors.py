import open3d as o3d

# Read the .ply file
mesh = o3d.io.read_triangle_mesh("data\output\test\batch_0\d_sg_only_xy_mesh_classification.ply")

# Check if the mesh has vertex colors
if mesh.has_vertex_colors():
    # Get the vertex colors as a numpy array
    vertex_colors = mesh.vertex_colors

    # Print the first 10 vertex colors
    print(vertex_colors[:10])
else:
    print("Mesh does not have vertex colors.")
