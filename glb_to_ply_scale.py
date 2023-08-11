# scales glb and jpg, converts to ply

import open3d as o3d
import numpy as np
import os

def scale_and_convert_to_ply(glb_file, jpg_file, output_folder):
    # Load the glb file
    try:
        mesh = o3d.io.read_triangle_mesh(glb_file)
    except RuntimeError as e:
        print("Error loading .glb file:", e)
        return

    # Check if the mesh has zero vertices
    if len(mesh.vertices) == 0:
        print("Mesh has zero vertices. Aborting.")
        return

    # Get the bounding box of the mesh
    bbox = mesh.get_axis_aligned_bounding_box()

    # Calculate the scale factor to make the mesh at least 50x50
    scale_factor = max(50 / (bbox.max_bound[0] - bbox.min_bound[0] + 1e-9),
                       50 / (bbox.max_bound[1] - bbox.min_bound[1] + 1e-9),
                       50 / (bbox.max_bound[2] - bbox.min_bound[2] + 1e-9))

    # Scale the mesh
    mesh.scale(scale_factor, center=bbox.get_center())

    # Save the scaled mesh as a .ply file
    ply_file = os.path.join(output_folder, os.path.splitext(os.path.basename(glb_file))[0] + "_scaled.ply")
    o3d.io.write_triangle_mesh(ply_file, mesh)

    # Save the jpg texture in the output folder
    jpg_output = os.path.join(output_folder, os.path.basename(jpg_file))
    with open(jpg_file, 'rb') as src:
        with open(jpg_output, 'wb') as dest:
            dest.write(src.read())

    print("Scaled mesh saved to:", ply_file)
    print("Texture saved to:", jpg_output)

# Replace the paths with your actual input .glb and .jpg files
glb_file = "python_files\singapore.glb"
jpg_file = "python_files\singapore.jpg"

# Replace "output_folder" with the path to the folder where you want to save the output files
output_folder = "python_files\converted"

# Call the function to scale and convert the .glb and .jpg files to .ply format
scale_and_convert_to_ply(glb_file, jpg_file, output_folder)
