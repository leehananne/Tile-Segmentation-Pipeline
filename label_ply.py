'''
    check rgb color of face and add corresponding labels
    face colours are given as normalised values (0 to 1)
 
    label number    label               rgb
        [0]         unclassified        0 0 0 
        [1]         terrain             0.666667 0.333333 0
        [2]         high vegetation     0 1 0
        [3]         building            1 1 0
        [4]         water               0 1 1
        [5]         car                 1 0 1
        [6]         boat                0 0 0.6
'''

import os
import shutil

def label_ply_file(input_file_name, output_file_name):
    """
    label a PLY file based on RGB values and save the labeled file.

    args:
        input_file_name (str): The path to the input PLY file.
        output_file_name (str): The path to save the labeled PLY file.

    returns:
        None
    """
    # RGB values and corresponding labels
    rgb_labels = {
        (0, 0, 0): 0,                   # unclassified
        (0.666667, 0.333333, 0): 1,     # terrain
        (0, 1, 0): 2,                   # vegetation
        (1, 1, 0): 3,                   # building
        (0, 1, 1): 4,                   # water
        (1, 0, 1): 5,                   # car
        (0, 0, 0.6): 6                  # boat
    }

    epsilon = 1e-6  # adjust value based on tolerance requirement

    with open(input_file_name, 'r') as input_file, open(output_file_name, 'w') as output_file:
        for input_line in input_file:
            elements = input_line.strip().split()

            if len(elements) < 15:
                output_file.write(input_line)
            elif len(elements) > 15:
                r, g, b = float(elements[11]), float(elements[12]), float(elements[13])

                # find the label based on RGB values
                label = rgb_labels.get((r, g, b), -1)  # Default to -1 for unknown

                # update the label in the elements list
                elements[20] = label

                # write the modified elements to the output file
                output_line = ' '.join(map(str, elements)) + '\n'
                output_file.write(output_line)

def process_files_in_folder(folder_path):
    """
    process all PLY files in a folder.

    args:
        folder_path (str): The path to the folder containing PLY files.

    returns:
        None
    """
    # create a "labelled" folder if it doesn't exist to store output files 
    labelled_folder = os.path.join(folder_path, 'labelled')
    if not os.path.exists(labelled_folder):
        os.makedirs(labelled_folder)

    # list all files in the folder
    file_list = os.listdir(folder_path)

    # iterate through each file and process it
    for filename in file_list:
        file_path = os.path.join(folder_path, filename)

        # ensure the item in the folder is a file (not a subfolder)
        if os.path.isfile(file_path) and filename.endswith('_classification.ply') and not filename.endswith('_error.ply'):
            print("Processing file:", filename)
            output_file_name = os.path.join(labelled_folder, filename.replace('.ply', '_labelled.ply'))
            label_ply_file(file_path, output_file_name)

if __name__ == "__main__":

    # single file
    input_file_name = "D:/sums/SUMS_TUDelft/data/output/test/submesh0_2_mesh_classification.ply"
    output_file_name = input_file_name.replace('.ply', '_labelled.ply')
    label_ply_file(input_file_name, output_file_name)

    # for a batch of files in a folder
    folder_path = "D:/sums/SUMS_TUDelft/data/output/test"
    process_files_in_folder(folder_path)
