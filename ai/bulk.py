import os
import tempfile
import pandas as pd
from google import genai

def build_directory_map(input_folder):
    lines = []
    for root, _, files in os.walk(input_folder):
        rel_root = os.path.relpath(root, input_folder)
        if rel_root == '.':
            rel_root = os.path.basename(input_folder)
        lines.append(f"{rel_root}/")
        for file in files:
            lines.append(f"    {file}")
    return "\n".join(lines)

def upload_pdfs(input_folder, client):
    pdf_files = []
    for root, _, files in os.walk(input_folder):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))
    uploaded_files = []
    for pdf_path in pdf_files:
        try:
            uploaded = client.files.upload(
                file=pdf_path,
                config=dict(mime_type='application/pdf')
            )
            # Store tuple: (file label, uploaded file object)
            uploaded_files.append( (os.path.basename(pdf_path), uploaded) )
            print(f"Uploaded PDF: {os.path.basename(pdf_path)}")
        except Exception as e:
            print(f"Failed to upload PDF {os.path.basename(pdf_path)}: {e}")
    return uploaded_files

def upload_excels_as_csv(input_folder, client):
    excel_exts = ('.xls', '.xlsx')
    excel_files = []
    for root, _, files in os.walk(input_folder):
        for file in files:
            if file.lower().endswith(excel_exts):
                excel_files.append(os.path.join(root, file))
    uploaded_files = []
    for excel_path in excel_files:
        try:
            df = pd.read_excel(excel_path)
            with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
                csv_path = tmp.name
                df.to_csv(csv_path, index=False)
            uploaded = client.files.upload(
                file=csv_path,
                config=dict(mime_type='text/csv')
            )
            uploaded_files.append( (os.path.basename(excel_path), uploaded) )
            print(f"Excel converted & uploaded as CSV: {os.path.basename(excel_path)}")
            os.unlink(csv_path)
        except Exception as e:
            print(f"Failed to process Excel {os.path.basename(excel_path)}: {e}")
    return uploaded_files

def build_gemini_contents(labeled_files, directory_map, instructions):
    """
    labeled_files: list of (label, file_obj)
    directory_map: str
    instructions: str
    Returns list for Gemini contents, interleaving label and file.
    """
    parts = []
    # Optional: add directory map at the start if needed
    if directory_map:
        parts.append(f"Directory of files:\n{directory_map}\n")
    # Interleave file labels and file objects
    for label, file_obj in labeled_files:
        parts.extend([
            f"--- FILE: {label} ---",
            file_obj,
            "\n"
        ])
    # Add your prompt/instructions at the end
    parts.append(instructions)
    return parts

def analyze_uploaded_files(labeled_files, input_folder, client):
    if not labeled_files:
        print("No files to analyze.")
        return

    directory_map = build_directory_map(input_folder)
    instructions = (
        "Now, extract the full manufacturing requirements for EACH component. Including the quantity. "
        "Always refer to each file using the exact filename label above."
    )
    contents = build_gemini_contents(labeled_files, directory_map, instructions)
    print("\n\n" + contents)
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
    )
    print(response.text)

if __name__ == "__main__":
    folder = input("Enter folder path to scan: ").strip()
    if not os.path.isdir(folder):
        print("Invalid directory.")
    elif "GOOGLE_API_KEY" not in os.environ:
        print("Set GOOGLE_API_KEY in your environment variables.")
    else:
        api_key = os.environ["GOOGLE_API_KEY"]
        client = genai.Client(api_key=api_key)
        uploaded_pdfs   = upload_pdfs(folder, client)
        uploaded_excels = upload_excels_as_csv(folder, client)
        all_uploaded    = uploaded_pdfs + uploaded_excels
        analyze_uploaded_files(all_uploaded, folder, client)