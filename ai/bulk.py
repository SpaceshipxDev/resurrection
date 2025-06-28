import os
import tempfile
import pandas as pd
from google import genai

def scan_files(input_folder):
    """Return a list of (relative_path, abs_path, ext) for all files under input_folder"""
    file_list = []
    for root, _, files in os.walk(input_folder):
        for file in files:
            abs_path = os.path.join(root, file)
            rel_path = os.path.relpath(abs_path, input_folder)
            # extension: .pdf, .stp, etc
            ext = os.path.splitext(file)[-1].lower()
            file_list.append((rel_path, abs_path, ext))
    return file_list

def upload_files(file_list, client):
    """Uploads PDFs, Excels (as CSV), PPTX (as PDF). Returns dict: rel_path -> file_obj or None."""
    uploaded = {}
    for rel_path, abs_path, ext in file_list:
        try:
            if ext == '.pdf':
                obj = client.files.upload(file=abs_path, config=dict(mime_type='application/pdf'))
                uploaded[rel_path] = obj
                print(f"Uploaded PDF: {rel_path}")
            elif ext in ('.xls', '.xlsx'):
                df = pd.read_excel(abs_path)
                with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
                    csv_path = tmp.name
                    df.to_csv(csv_path, index=False)
                obj = client.files.upload(file=csv_path, config=dict(mime_type='text/csv'))
                uploaded[rel_path] = obj
                print(f"Excel converted & uploaded as CSV: {rel_path}")
                os.unlink(csv_path)
            elif ext == '.pptx':
                output_dir = os.path.dirname(abs_path)
                base_name = os.path.splitext(os.path.basename(abs_path))[0]
                pdf_path = os.path.join(output_dir, base_name + '.pdf')
                cmd = [
                    "libreoffice", "--headless", "--convert-to", "pdf", "--outdir", output_dir, abs_path
                ]
                result = os.system(' '.join(f'"{c}"' if ' ' in c else c for c in cmd))
                if result != 0 or not os.path.isfile(pdf_path):
                    raise RuntimeError(f"LibreOffice failed for {rel_path}")
                obj = client.files.upload(file=pdf_path, config=dict(mime_type='application/pdf'))
                uploaded[rel_path] = obj
                print(f"PPTX converted & uploaded as PDF: {rel_path}")
                os.unlink(pdf_path)
            else:
                uploaded[rel_path] = None  # Not uploaded, e.g., .stp
        except Exception as e:
            print(f"Failed to process {rel_path}: {e}")
            uploaded[rel_path] = None
    return uploaded


def build_gemini_contents(uploaded_files: dict, repo_name: str, instructions: str):
    """
    uploaded_files: dict of rel_path -> file_obj or None
    repo_name: string
    instructions: string
    Returns: list of prompt parts for Gemini API
    """
    parts = []
    parts.append(f"Project Directory: {repo_name}/\n")
    for rel_path, file_obj in uploaded_files.items():
        if file_obj is not None:
            parts.extend([
                f"--- FILE: {rel_path} ---",
                file_obj,
                "\n"
            ])
        else:
            parts.extend([
                f"--- FILE: {rel_path} ---",
                "\n [preview unavailable] "
                "\n"
            ])
    parts.append(instructions)
    return parts


def analyze_uploaded_files(uploaded_files: dict, repo_name: str, client):
    if not uploaded_files:
        print("No files to analyze.")
        return

    instructions = (
        "From the uploade file(s), Carefully extract the full manufacturing requirements for EACH component, including quantity. "
        "If information is missing, make it clear. Also, briefly describe what each component looks like if info is available."
    )
    contents = build_gemini_contents(uploaded_files, repo_name, instructions)
    printable = [x for x in contents if isinstance(x, str)]
    print("\n\n" + "prompt:\n" + "\n".join(printable))

    response = client.models.generate_content(
        model="gemini-2.5-pro",
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
        
        repo_name = os.path.basename(os.path.abspath(folder))
        file_list = scan_files(folder)
        uploaded_files = upload_files(file_list, client)
        analyze_uploaded_files(uploaded_files, repo_name, client)