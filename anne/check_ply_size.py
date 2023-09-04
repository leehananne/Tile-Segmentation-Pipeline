import open3d as o3d
import numpy as np

# Read the .ply file
ply_path = "python_files\singapore_4.ply"
point_cloud = o3d.io.read_point_cloud(ply_path)

# Get the vertex coordinates as a numpy array
vertices = np.asarray(point_cloud.points)

# Find the minimum and maximum coordinates for x, y, and z
min_x, min_y, min_z = vertices.min(axis=0)
max_x, max_y, max_z = vertices.max(axis=0)

# Calculate the width and length of the model
width = max_x - min_x
length = max_y - min_y

# Check if the size is at least 50x50 meters
if width >= 50 and length >= 50:
    # print("The size of the .ply file is at least 50x50 meters.")
    print("The size of the .ply file is", width, "meters wide and", length, "meters long.")
else:
    print("The size of the .ply file is", width, "meters wide and", length, "meters long.")
