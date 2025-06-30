import os
import tempfile
import pandas as pd
from google import genai
import cadquery as cq
import pyvista as pv

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

def convert_stp_to_image(stp_path, output_image_path):
    """Convert STP file to PNG image via STL conversion"""
    try:
        # Import STP and convert to STL
        shape = cq.importers.importStep(stp_path)
        
        # Create temporary STL file
        with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as tmp_stl:
            stl_path = tmp_stl.name
            cq.exporters.export(shape, stl_path)
        
        # Set up PyVista plotter for off-screen rendering
        plotter = pv.Plotter(off_screen=True)
        
        # Load and render the STL
        mesh = pv.read(stl_path)
        plotter.add_mesh(mesh, color='tan', show_edges=False)
        plotter.camera_position = 'iso'  # Isometric view
        
        # Save screenshot
        plotter.screenshot(output_image_path, window_size=[1920, 1080])
        plotter.close()
        
        # Clean up temporary STL
        os.unlink(stl_path)
        
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
                    obj = client.files.upload(file=png_path, config=dict(mime_type='image/png'))
                    uploaded[rel_path] = obj
                    print(f"STP converted & uploaded as PNG: {rel_path}")
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

def save_html_output(html_content, repo_name):
    """Save the HTML content to a file"""
    output_filename = f"{repo_name}_manufacturing_components.html"
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"\nHTML spreadsheet saved as: {output_filename}")
        return output_filename
    except Exception as e:
        print(f"Error saving HTML file: {e}")
        return None

def analyze_uploaded_files(uploaded_files: dict, repo_name: str, client):
    if not uploaded_files:
        print("No files to analyze.")
        return

    instructions = (
        """From the uploaded customer files, analyze all components that need to be manufactured and create a complete HTML spreadsheet using this EXACT standard format.

        IMPORTANT: Generate a complete, standalone HTML document with this EXACT table structure:

        STANDARD SPREADSHEET COLUMNS (must be exactly these 4 columns):
        1. 产品名称 (STP filename without extension)
        2. 材料 (Material type - e.g., Aluminum, Steel, Stainless Steel, etc.)
        3. 数量 (Quantity needed)
        4. 规格 (Finishing/specifications - e.g., Anodized, Powder Coated, As Machined, etc.)

        HTML REQUIREMENTS:
        - Complete HTML document with <!DOCTYPE html>
        - Professional CSS styling with clean table appearance
        - Fixed header row
        - Alternating row colors (white/light gray)
        - Bordered cells with proper spacing
        - UTF-8 encoding for Chinese characters
        - Print-friendly layout

        ANALYSIS REQUIREMENTS:
        - Analyze each STP file thoroughly
        - One row per STP file
        - Extract realistic material and quantity requirements
        - Specify appropriate finishing based on component analysis

        Generate ONLY the complete HTML code with proper Chinese character support - no explanation text before or after."""
    )
    
    contents = build_gemini_contents(uploaded_files, repo_name, instructions)
    printable = [x for x in contents if isinstance(x, str)]
    print("\n\n" + "Sending request to Gemini for HTML spreadsheet generation...")

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
        )
        
        html_content = response.text
        
        # Save the HTML to a file
        output_file = save_html_output(html_content, repo_name)
        
        if output_file:
            print(f"\nGenerated HTML spreadsheet successfully!")
            print(f"You can open '{output_file}' in your web browser to view the component analysis.")
        else:
            print("\nHTML content generated but couldn't save to file. Here's the content:")
            print(html_content)
            
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