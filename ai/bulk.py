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

def upload_csvs(input_folder, api_key):
    csv_files = []
    for root, _, files in os.walk(input_folder):
        for file in files:
            if file.lower().endswith('.csv'):
                csv_files.append(os.path.join(root, file))
    if not csv_files:
        print("No CSV files found.")
        return []
    client = genai.Client(api_key=api_key)
    uploaded_files = []
    for csv_path in csv_files:
        try:
            uploaded = client.files.upload(
                file=csv_path,
                config=dict(mime_type='text/csv')
            )
            uploaded_files.append(uploaded)
            print(f"Uploaded: {os.path.basename(csv_path)}")
        except Exception as e:
            print(f"Failed to upload {os.path.basename(csv_path)}: {e}")
    return uploaded_files

def upload_excels_as_csv(input_folder, api_key):
    excel_exts = ('.xls', '.xlsx')
    excel_files = []
    for root, _, files in os.walk(input_folder):
        for file in files:
            if file.lower().endswith(excel_exts):
                excel_files.append(os.path.join(root, file))
    if not excel_files:
        print("No Excel files found.")
        return []
    client = genai.Client(api_key=api_key)
    uploaded_files = []
    for excel_path in excel_files:
        try:
            # Convert to CSV first (use first sheet)
            df = pd.read_excel(excel_path)
            with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as tmp:
                csv_path = tmp.name
                df.to_csv(csv_path, index=False)
            uploaded = client.files.upload(
                file=csv_path,
                config=dict(mime_type='text/csv')
            )
            uploaded_files.append(uploaded)
            print(f"Excel converted & uploaded as CSV: {os.path.basename(excel_path)}")
            os.unlink(csv_path)
        except Exception as e:
            print(f"Failed to process {os.path.basename(excel_path)}: {e}")
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
        # Upload CSVs
        uploaded_csvs = upload_csvs(folder, api_key)
        # Upload Excels (as CSV)
        uploaded_excels = upload_excels_as_csv(folder, api_key)
        all_uploaded = uploaded_csvs + uploaded_excels
        analyze_uploaded_files(all_uploaded, folder, api_key)