def read_ply_file(file_path):
    vertices = []
    with open(file_path, 'r') as file:
        is_vertex_section = False
        for line in file:
            if line.startswith('element vertex'):
                is_vertex_section = True
                continue
            if is_vertex_section and not line.startswith('property') and len(line.strip().split()) == 5:
                vertices.append(line.strip().split())

    return vertices

def move_ply(vertices, file_path):
    # Convert vertex coordinates to floating-point numbers
    vertices = [[float(coord) for coord in vertex] for vertex in vertices]

    # Calculate the minimum x, y, and z values
    min_x = min(v[0] for v in vertices)
    min_y = min(v[1] for v in vertices)
    min_z = min(v[2] for v in vertices)

    # Calculate the maximum absolute translation value to move to the positive axis
    max_translate = max(max(abs(v[0]), abs(v[1]), abs(v[2])) for v in vertices) 

    # Apply translation to move all vertices to the positive axis
    translated_vertices = [
        [str(v[0] + max_translate), str(v[1] + max_translate), str(v[2] + max_translate)] + v[3:]
        for v in vertices
    ]

    # The translated_vertices now contains the coordinates shifted to the positive x, y, and z axis
    # print(translated_vertices)

    # Extract the input file name from the original file path
    input_file_path = file_path
    input_file_name = input_file_path.split(".")[0]

    # Create the output file path with the input file name
    output_file_path = f"{input_file_name}_shifted.ply"

    # Create a new file with modified lines
    with open(input_file_path, 'r') as infile, open(output_file_path, 'w') as outfile:
        is_vertex_section = False
        for line in infile:
            if line.startswith('element vertex'):
                is_vertex_section = True
                outfile.write(line)
                continue
            if is_vertex_section and not line.startswith('property') and len(line.strip().split()) == 5:
                vertex = line.strip().split()[:3]
                translated_vertex = [str(float(v) + max_translate) for v in vertex[:3]] + vertex[3:]
                outfile.write(" ".join(translated_vertex) + "\n")
            else:
                outfile.write(line)
    
    # Read and print the contents of the output file
    with open(output_file_path, 'r') as output_file:
        output_contents = output_file.read()

    print(output_contents)
    print("Output file saved to:", output_file_path)

if __name__ == "__main__":
    ply_file_path = "python_files/singapore_4.ply"
    vertices = read_ply_file(ply_file_path)
    print("Vertices:")
    # for vertex in vertices:
        # print(vertex)
    move_ply(vertices, ply_file_path)
    
    
