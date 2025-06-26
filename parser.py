

import os

def generate_file_list(input_folder, output_file='file_list.txt'):
    """
    Scans the input_folder for specific file types and writes their relative paths to an output file.
    """
    allowed_extensions = ('.stp', '.dwg', '.pdf', '.xlsx')
    
    with open(output_file, 'w') as f:
        for root, _, files in os.walk(input_folder):
            for file in files:
                if file.lower().endswith(allowed_extensions):
                    relative_path = os.path.relpath(os.path.join(root, file), input_folder)
                    f.write(f'{relative_path}\n')

    print(f"File list generated at {output_file}")

if __name__ == "__main__":
    # You can change this to the desired input folder
    # For example, if you want to process the current directory, use '.'
    # Or ask the user for input:
    input_folder = input("Enter the path to the folder to scan: ")
    if not os.path.isdir(input_folder):
        print(f"Error: The provided path '{input_folder}' is not a valid directory.")
    else:
        generate_file_list(input_folder)

