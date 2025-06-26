import os
from google import genai


def build_directory_map(input_folder):
    """
    Builds a tree map of all files under input_folder as a string.
    """
    lines = []
    for root, _, files in os.walk(input_folder):
        rel_root = os.path.relpath(root, input_folder)
        if rel_root == '.':
            rel_root = os.path.basename(input_folder)
        lines.append(f"{rel_root}/")
        for file in files:
            lines.append(f"    {file}")
    return "\n".join(lines)


def analyze_pdfs_with_gemini(input_folder, api_key):
    """
    Scans the input_folder for PDF files and analyzes them with Gemini.
    """
    pdf_files = []
    # Find all PDFs
    for root, _, files in os.walk(input_folder):
        for file in files:
            if file.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))

    if not pdf_files:
        print("No PDF files found.")
        return

    client = genai.Client(api_key=api_key)
    uploaded_files = []
    print(f"Uploading {len(pdf_files)} PDF files to Gemini...")

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

    if not uploaded_files:
        print("No files were successfully uploaded.")
        return

    print("Processing PDFs with Gemini...")

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
        analyze_pdfs_with_gemini(folder, os.environ["GOOGLE_API_KEY"])