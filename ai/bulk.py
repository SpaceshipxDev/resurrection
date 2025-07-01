import os
import tempfile
import pandas as pd
from google import genai
import cadquery as cq
import pyvista as pv
import shutil
import time 

def scan_files(input_folder):
    """Return a list of (relative_path, abs_path, ext) for all files under input_folder"""
    file_list = []
    for root, _, files in os.walk(input_folder):
        for file in files:
            abs_path = os.path.join(root, file)
            rel_path = os.path.relpath(abs_path, input_folder)
            ext = os.path.splitext(file)[-1].lower()
            file_list.append((rel_path, abs_path, ext))
    return file_list

def convert_stp_to_image(stp_path, output_image_path):
    """
    Convert STP file to PNG image via STL conversion.
    STL is saved permanently in generated_stl folder next to STP.
    """
    try:
        # Import STP and convert to STL
        shape = cq.importers.importStep(stp_path)
        
        # --- SAVE STL PERMANENTLY ---
        stl_dir = os.path.join(os.path.dirname(stp_path), "generated_stl")
        os.makedirs(stl_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(stp_path))[0]
        stl_path = os.path.join(stl_dir, base_name + ".stl")
        cq.exporters.export(shape, stl_path)
        print(f"STL saved to: {stl_path}")

        # --- WAIT FOR FILE TO FULLY FLUSH ---
        time.sleep(1)
        # Optional: Wait for file size to stabilize
        prev_size = -1
        for _ in range(5):
            size = os.path.getsize(stl_path)
            if size == prev_size:
                break
            prev_size = size
            time.sleep(0.5)

        # --------- RELOAD STL FROM DISK -----------
        STL_FILE = stl_path
        OUTPUT_IMAGE="made.png" 

        plotter = pv.Plotter(off_screen=True)
        mesh = pv.read(STL_FILE)
        plotter.add_mesh(mesh, color="tan", show_edges=False)
        plotter.camera_position = "iso"
        plotter.screenshot(OUTPUT_IMAGE, window_size=[1920, 1080])
        plotter.close()
        return True

    except Exception as e:
        print(f"Error converting STP to image: {e}")
        return False

def upload_files(file_list, client):
    """
    Uploads PDFs, Excels (as CSV), PPTX (as PDF), STP (as PNG).
    Returns dict: rel_path -> file_obj or None.
    """
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
                
            elif ext == '.stp':
                # Convert STP to PNG image
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_img:
                    png_path = tmp_img.name

                if convert_stp_to_image(abs_path, png_path):
                    obj = client.files.upload(file=png_path, config=dict(mime_type='image/png'))
                    uploaded[rel_path] = obj
                    print(f"STP converted & uploaded as PNG: {rel_path}")

                    # --- SAVE PERMANENT PNG COPY ---
                    save_dir = os.path.join(os.path.dirname(abs_path), "generated_pngs")
                    os.makedirs(save_dir, exist_ok=True)
                    base_name = os.path.splitext(os.path.basename(abs_path))[0] + ".png"
                    save_path = os.path.join(save_dir, base_name)
                    shutil.copy(png_path, save_path)
                    print(f"Saved PNG to: {save_path}")
                    # --- END ---

                    os.unlink(png_path)
                else:
                    uploaded[rel_path] = None
                    print(f"Failed to convert STP: {rel_path}")
                    
            else:
                uploaded[rel_path] = None  # Not supported
                
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
            # Add note for STP files that they've been converted to images
            file_note = ""
            if rel_path.lower().endswith('.stp'):
                file_note = " (converted to image for analysis)"
            
            parts.extend([
                f"--- FILE: {rel_path}{file_note} ---",
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
        """From the uploaded customer files, carefully think through and understand all information, and tell me exactly what components my cnc 
        factory needs to manufacture for my customer. specify each component's file path as well."""
    )
    contents = build_gemini_contents(uploaded_files, repo_name, instructions)
    printable = [x for x in contents if isinstance(x, str)]
    print("\n\n" + "prompt:\n" + "\n".join(printable))

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
        
        repo_name = os.path.basename(os.path.abspath(folder))
        file_list = scan_files(folder)
        uploaded_files = upload_files(file_list, client)
        analyze_uploaded_files(uploaded_files, repo_name, client)