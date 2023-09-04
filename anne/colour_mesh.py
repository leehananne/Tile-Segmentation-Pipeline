# using colours of vertex faces, 
# apply colour to the mesh texture to label it

import open3d as o3d 
import numpy as np

input_file_name = "D:/Anne_UnityProjects/SUMS_TUDelft/data/output/test/batch_0/d_sg_only_xy_mesh_classification.ply"

mesh_in = o3d.io.read_triangle_mesh(input_file_name)

with open(input_file_name, 'r') as file:
    line_num = 19161
    for line in file:
        elements = line.strip().split()

        # Check if the line has 15 elements
        if len(elements) == 15:
            line_num +=1
            # Extract RGB values from 4th, 5th, and 6th indices
            r, g, b = float(elements[4]), float(elements[5]), float(elements[6])
            
            # Check if any of the RGB values are negative
            if r < 0 or g < 0 or b < 0:
                print(f"Line {line_num}: {elements[4]}, {elements[5]}, {elements[6]}")
    else:
        print("All values are within 0 and 1")
            