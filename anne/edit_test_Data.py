# remove the generated labels in test data

import os

def extract_lines_with_prefix_3(file_path):
    # Read the .ply file and extract lines starting with '3'
    lines_with_prefix_3 = []
    with open(file_path, 'r') as file:
        is_vertex_section = False
        for line in file:
            if line.startswith('element vertex'):
                is_vertex_section = True
                continue
            if is_vertex_section and line.strip().startswith('3'):
                # Extract the first 4 elements from the line and join them with spaces
                line_with_prefix_3 = ' '.join(line.strip().split()[:4])
                lines_with_prefix_3.append(line_with_prefix_3)

    return lines_with_prefix_3

def save_lines_to_ply(file_path, lines_with_prefix_3):
    # Extract the input file name from the original file path
    input_file_name = os.path.splitext(os.path.basename(file_path))[0]

    # Create the output file name with the _modified.ply suffix
    output_file_name = f"{input_file_name}_modified.ply"
    output_file_path = os.path.join(os.getcwd(), output_file_name)

    # Write the lines starting with '3' and only the first 4 elements to the new .ply file
    with open(file_path, 'r') as infile, open(output_file_path, 'w') as outfile:
        is_vertex_section = False
        for line in infile:
            if line.startswith('element vertex'):
                is_vertex_section = True
                outfile.write(line)
                continue
            if is_vertex_section and line.strip().startswith('3'):
                # Extract the first 4 elements from the line and write to the output file
                outfile.write(' '.join(line.strip().split()[:4]) + "\n")
            else:
                outfile.write(line)

    print("Modified file saved to:", output_file_path)

if __name__ == "__main__":
    ply_file_path = "data\data-input-test\Tile_+1991_+2693_groundtruth_L1.ply"
    lines_with_prefix_3 = extract_lines_with_prefix_3(ply_file_path)
    save_lines_to_ply(ply_file_path, lines_with_prefix_3)