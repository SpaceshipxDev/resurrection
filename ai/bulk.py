import os
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


def upload_pdfs(input_folder, api_key):
    pdf_files = []
    for root, _, files in os.walk(input_folder):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))

    if not pdf_files:
        print("No PDF files found.")
        return []

    client = genai.Client(api_key=api_key)
    uploaded_files = []
    for pdf_path in pdf_files:
        try:
            uploaded_file = client.files.upload(
                file=pdf_path,
                config=dict(mime_type='application/pdf')
            )
            uploaded_files.append(uploaded_file)
            print(f"Uploaded: {os.path.basename(pdf_path)}")
        except Exception as e:
            print(f"Failed to upload {os.path.basename(pdf_path)}: {e}")
    return uploaded_files


def analyze_uploaded_files(uploaded_files, input_folder, api_key):
    if not uploaded_files:
        print("No files to analyze.")
        return

    client = genai.Client(api_key=api_key)
    directory_map = build_directory_map(input_folder)
    prompt = (
        f"Directory Map of all files and folders in this batch:\n"
        f"{directory_map}\n\n"
        f"Now, extract the full manufacturing requirements for EACH component."
    )
    contents = uploaded_files + [prompt]
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
        # Phase 1: Upload PDFs
        uploaded = upload_pdfs(folder, api_key)
        # Phase 2: Analyze (if you want to call this now; in future you could save and load uploaded handles)
        analyze_uploaded_files(uploaded, folder, api_key)