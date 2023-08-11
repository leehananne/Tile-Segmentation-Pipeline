import open3d as o3d
import os
import numpy as np
from PIL import Image

# Read the .ply file
ply_path = "python_files\singapore.ply"
mesh = o3d.io.read_triangle_mesh(ply_path)

jpg_path = "python_files\singapore.jpg"
img = Image.open(jpg_path)

# Get the extents of the mesh along each axis
min_bound = np.min(np.asarray(mesh.vertices), axis=0)
max_bound = np.max(np.asarray(mesh.vertices), axis=0)
mesh_width = max_bound[0] - min_bound[0]
mesh_length = max_bound[1] - min_bound[1]

print("mesh width: ", mesh_width)
print("mesh length: ", mesh_length)

# Calculate the scaling factors to achieve a minimum width and length of 50 meters
target_width = 55.0
target_length = 55.0
scale_factor = max(target_width / mesh_width, target_length / mesh_length)
print("scale factor: ", scale_factor)

# Scale the mesh while preserving its aspect ratio
mesh.scale(scale_factor, center=min_bound)
print("scaling mesh ----------------------")

# Get the input file name without the extension
input_file_name = os.path.splitext(os.path.basename(ply_path))[0]
print("input file name: ", input_file_name)

# Create the output file name with the _scaled.ply suffix
output_file_name = f"{input_file_name}_scaled.ply"
output_path = os.path.join(os.getcwd(), output_file_name)
o3d.io.write_triangle_mesh(output_path, mesh)

# Print the new width and length of the scaled tile
new_width = mesh_width * scale_factor
new_length = mesh_length * scale_factor
print("New width of the tile:", new_width, "meters")
print("New length of the tile:", new_length, "meters")
print("Scaled file saved to:", output_path)

# Resize the texture jpg
img_resized = img.resize((int(img.width * scale_factor), int(img.height * scale_factor)))

# Create the output file name with the _scaled.jpg suffix
output_jpg_name = f"{input_file_name}_scaled.jpg"
output_jpg_path = os.path.join(os.getcwd(), output_jpg_name)
img_resized.save(output_jpg_path)

# Print the new width and height of the scaled texture
new_width = img.width * scale_factor
new_height = img.height * scale_factor
print("New width of the texture:", new_width, "pixels")
print("New height of the texture:", new_height, "pixels")
print("Scaled texture saved to:", output_jpg_path)