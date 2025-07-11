import os
import shutil
import tempfile
import pandas as pd
from google import genai
import cadquery as cq
import pyvista as pv

# ---- CONFIG: Set your PNG output directory here ----
OUTPUT_IMAGES_DIR = os.path.join(os.getcwd(), "generated_pngs")
os.makedirs(OUTPUT_IMAGES_DIR, exist_ok=True)

OUTPUT_STL_DIR = os.path.join(os.getcwd(), "generated_stls")
os.makedirs(OUTPUT_STL_DIR, exist_ok=True)
# ---------------------------------------------------

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
    """Convert STP file to PNG image via STL conversion, saving STL as permanent file."""
    try:
        # Import STP and convert to STL
        shape = cq.importers.importStep(stp_path)

        # Set up STL path (named after the original file)
        base_name = os.path.splitext(os.path.basename(stp_path))[0]
        stl_path = os.path.join(OUTPUT_STL_DIR, f"{base_name}.stl")
        cq.exporters.export(shape, stl_path)

        # Set up PyVista plotter for off-screen rendering
        plotter = pv.Plotter(off_screen=True)
        mesh = pv.read(stl_path)
        plotter.add_mesh(mesh, color='tan', show_edges=False)
        plotter.camera_position = 'iso'  # Isometric view

        # Save screenshot
        plotter.screenshot(output_image_path, window_size=[1920, 1080])
        plotter.close()

        # No temp STL to delete; file is permanent now!
        return True

    except Exception as e:
        print(f"Error converting STP to image: {e}")
        return False


def upload_files(file_list, client):
    """Uploads PDFs, Excels (as CSV), PPTX (as PDF), STP (as PNG). Returns dict: rel_path -> file_obj or None."""
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
                    # Save a permanent copy of PNG
                    final_png_name = os.path.splitext(os.path.basename(rel_path))[0] + ".png"
                    final_png_path = os.path.join(OUTPUT_IMAGES_DIR, final_png_name)
                    shutil.copy2(png_path, final_png_path)
                    
                    obj = client.files.upload(file=png_path, config=dict(mime_type='image/png'))
                    uploaded[rel_path] = obj
                    print(f"STP converted & uploaded as PNG: {rel_path} (saved at {final_png_path})")
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

def analyze_uploaded_files(uploaded_files: dict, repo_name: str, client):
    if not uploaded_files:
        print("No files to analyze.")
        return

    instructions = (
        """
        From the customer's uploaded folder, carefully analyze it and seperate it into individual components with their respective attributes.  
        Generate the HTML rows (<tr> and <td> tags precisely) in simplified format as shown below. 

        Example of expected format:

        <tr>
            <td>产品名称</td>
            <td>材料</td>
            <td>数量</td>
            <td>规格</td>
        </tr>

        - Precisely one row per inferred component.
        - 产品名称 should be STP filename without ".stp".
        - 规格 refers to the surface finish. 
        - Infer  materials, quantities, and specifications.

        Provide ONLY exact HTML rows, no explanations or other markup at all.
        """
    )
    
    parts = []
    parts.append(f"Project Directory: {repo_name}/\n")
    for rel_path, file_obj in uploaded_files.items():
        if file_obj is not None:
            file_note = " (converted to image for analysis)" if rel_path.lower().endswith('.stp') else ""
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
    
    print("\n\nSending request to Gemini for HTML spreadsheet generation...")

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=parts,
        )

        html_rows = response.text.strip()
        if html_rows.startswith('html') and html_rows.endswith(''):
            html_rows = html_rows[7:-3].strip()
        elif html_rows.startswith('') and html_rows.endswith(''):
            lines = html_rows.split('\n')
            if len(lines) > 2:
                html_rows = '\n'.join(lines[1:-1])

        with open("template.html", "r", encoding="utf-8") as f:
            html_template = f.read()

        complete_html = html_template.replace("{{TABLE_BODY}}", html_rows)
        output_file = f"{repo_name}_components.html"
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(complete_html)
            
        print(f"✅ HTML spreadsheet generated: {output_file}")
        
    except Exception as e:
        print(f"Error generating HTML spreadsheet: {e}")

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
