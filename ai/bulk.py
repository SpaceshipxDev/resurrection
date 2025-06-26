import os
from google import genai
from google.genai import types

def generate_file_list(input_folder, output_file='file_list.txt'):
    """
    Scans the input_folder for specific file types and writes their relative paths to an output file.
    Returns lists of found files by type.
    """
    allowed_extensions = ('.stp', '.dwg', '.pdf', '.xlsx')
    
    files_by_type = {
        'pdf': [],
        'stp': [],
        'dwg': [],
        'xlsx': []
    }
    
    with open(output_file, 'w') as f:
        for root, _, files in os.walk(input_folder):
            for file in files:
                if file.lower().endswith(allowed_extensions):
                    relative_path = os.path.relpath(os.path.join(root, file), input_folder)
                    full_path = os.path.join(root, file)
                    
                    f.write(f'{relative_path}\n')
                    
                    # Categorize files
                    ext = file.lower().split('.')[-1]
                    if ext in files_by_type:
                        files_by_type[ext].append({
                            'relative_path': relative_path,
                            'full_path': full_path,
                            'filename': file
                        })
    
    print(f"File list generated at {output_file}")
    return files_by_type

def process_pdfs_with_gemini(pdf_files, input_folder):
    """
    Uploads PDF files to Gemini and extracts requirements.
    """
    if not pdf_files:
        print("No PDF files found to process.")
        return
    
    try:
        client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
        
        # Upload all PDFs
        uploaded_files = []
        print(f"Uploading {len(pdf_files)} PDF files to Gemini...")
        
        for pdf_info in pdf_files:
            try:
                uploaded_file = client.files.upload(
                    file=pdf_info['full_path'],
                    config=dict(mime_type='application/pdf')
                )
                uploaded_files.append(uploaded_file)
                print(f"Uploaded: {pdf_info['filename']}")
            except Exception as e:
                print(f"Failed to upload {pdf_info['filename']}: {e}")
        
        if not uploaded_files:
            print("No files were successfully uploaded.")
            return
        
        # Generate content with all uploaded PDFs
        print("Processing PDFs with Gemini...")
        
        # Create contents list with all uploaded files plus the prompt
        contents = uploaded_files + ["extract the full requirements of each component"]
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
        )
        
        # Save response to file
        output_file = os.path.join(input_folder, "gemini_requirements_analysis.txt")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("GEMINI REQUIREMENTS ANALYSIS\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Processed {len(uploaded_files)} PDF files:\n")
            for i, pdf_info in enumerate([pdf for pdf in pdf_files if i < len(uploaded_files)]):
                f.write(f"- {pdf_info['relative_path']}\n")
            f.write("\n" + "=" * 50 + "\n\n")
            f.write(response.text)
        
        print(f"Gemini analysis saved to: {output_file}")
        print(f"Response preview: {response.text[:200]}...")
        
    except KeyError:
        print("Error: GOOGLE_API_KEY environment variable not found.")
        print("Set it with: export GOOGLE_API_KEY='your-api-key'")
    except Exception as e:
        print(f"Error processing PDFs with Gemini: {e}")

def send_file_list_to_gemini(files_by_type, input_folder):
    """
    Sends the complete file inventory to Gemini for analysis.
    """
    try:
        client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
        
        # Create file inventory summary
        inventory_text = "FILE INVENTORY ANALYSIS:\n\n"
        
        for file_type, file_list in files_by_type.items():
            if file_list:
                inventory_text += f"{file_type.upper()} FILES ({len(file_list)}):\n"
                for file_info in file_list:
                    inventory_text += f"- {file_info['relative_path']}\n"
                inventory_text += "\n"
        
        prompt = f"""Analyze this file inventory from an engineering project repository:

                {inventory_text}

                Please provide:
                1. Project structure analysis
                2. Identified components and their file relationships
                3. Missing file types or gaps you notice
                4. Recommendations for file organization
                5. Potential workflow insights based on file types present"""
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt],
        )
        
        # Save inventory analysis
        output_file = os.path.join(input_folder, "gemini_inventory_analysis.txt")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("GEMINI FILE INVENTORY ANALYSIS\n")
            f.write("=" * 50 + "\n\n")
            f.write(response.text)
        
        print(f"Inventory analysis saved to: {output_file}")
        
    except Exception as e:
        print(f"Error sending inventory to Gemini: {e}")

if __name__ == "__main__":
    input_folder = input("Enter the path to the folder to scan: ")
    
    if not os.path.isdir(input_folder):
        print(f"Error: The provided path '{input_folder}' is not a valid directory.")
    else:
        # Generate file list and get categorized files
        files_by_type = generate_file_list(input_folder)
        
        # Print summary
        total_files = sum(len(files) for files in files_by_type.values())
        print(f"\nFound {total_files} files:")
        for file_type, file_list in files_by_type.items():
            print(f"  {file_type.upper()}: {len(file_list)} files")
        
        # Send file inventory to Gemini for analysis
        print("\nSending file inventory to Gemini...")
        send_file_list_to_gemini(files_by_type, input_folder)
        
        # Process PDFs with Gemini
        if files_by_type['pdf']:
            print(f"\nProcessing {len(files_by_type['pdf'])} PDF files with Gemini...")
            process_pdfs_with_gemini(files_by_type['pdf'], input_folder)
        else:
            print("\nNo PDF files found to process with Gemini.")
        
        print("\nProcessing complete!")