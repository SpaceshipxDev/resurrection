"""Simple end‑to‑end pipeline with nice previews
─────────────────────────────────────────────
• Walk an input folder, find engineering files
• For every STEP (`.stp`) render a clean isometric PNG preview (same basename)
• Upload everything to Gemini‑for‑workspace (`google‑genai`)
• Ask Gemini to return an HTML table **with an image column**
• Merge the rows into `template.html`, producing `<repo>_components.html`

Dependencies ▸  cadquery, pyvista, pandas, google‑genai, LibreOffice (only if you want .pptx→.pdf)
"""

import os
import tempfile
import pandas as pd
import cadquery as cq
import pyvista as pv
from google import genai

# ────────────────────────────────────────────────────────────────
# 1.  Collect files
# ────────────────────────────────────────────────────────────────

def scan_files(root: str):
    """Return a list (rel_path, abs_path, ext) for everything under *root*."""
    out = []
    for dirpath, _, files in os.walk(root):
        for fn in files:
            abs_path = os.path.join(dirpath, fn)
            rel_path = os.path.relpath(abs_path, root)
            out.append((rel_path, abs_path, os.path.splitext(fn)[1].lower()))
    return out

# ────────────────────────────────────────────────────────────────
# 2.  STEP → PNG preview (clean shading)
# ────────────────────────────────────────────────────────────────

def stp_to_png(stp_path: str, png_path: str) -> bool:
    try:
        print(f"Rendering: {stp_path}")
        shape = cq.importers.importStep(stp_path)
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
            stl_path = tmp.name
        cq.exporters.export(shape, stl_path, tolerance=0.05)

        mesh = pv.read(stl_path)
        mesh.clean(inplace=True)
        mesh.compute_normals(inplace=True)

        with pv.Plotter(off_screen=True, window_size=[800,800]) as plotter:
            plotter.set_background("white")
            plotter.add_mesh(mesh, color="#c0b090", smooth_shading=True, specular=0.2)
            plotter.camera_position = "iso"
            plotter.screenshot(png_path)

        os.unlink(stl_path)
        return True
    except Exception as exc:
        print(f"[STP→PNG ❌] {stp_path}: {exc}")
        return False
        
# ────────────────────────────────────────────────────────────────
# 3.  Upload logic
# ────────────────────────────────────────────────────────────────

def upload_files(file_list, client):
    """Upload supported files and STEP previews.

    Returns
    -------
    uploads : dict  { filename → file_obj }
    """
    uploads = {}

    for rel, abs_path, ext in file_list:
        try:
            # PDF ──────────────────────────────────
            if ext == ".pdf":
                uploads[rel] = client.files.upload(file=abs_path, config={"mime_type": "application/pdf"})
                print("⬆︎ PDF", rel)

            # Excel ────────────────────────────────
            elif ext in (".xls", ".xlsx"):
                df = pd.read_excel(abs_path)
                with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
                    csv_path = tmp.name
                df.to_csv(csv_path, index=False)
                uploads[rel] = client.files.upload(file=csv_path, config={"mime_type": "text/csv"})
                os.unlink(csv_path)
                print("⬆︎ Excel→CSV", rel)

            # PPTX → PDF ───────────────────────────
            elif ext == ".pptx":
                outdir = os.path.dirname(abs_path)
                pdf_path = os.path.join(outdir, os.path.splitext(os.path.basename(abs_path))[0] + ".pdf")
                cmd = ["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", outdir, abs_path]
                res = os.system(" ".join(f'"{c}"' if " " in c else c for c in cmd))
                if res or not os.path.isfile(pdf_path):
                    raise RuntimeError("LibreOffice conversion failed")
                uploads[rel] = client.files.upload(file=pdf_path, config={"mime_type": "application/pdf"})
                os.unlink(pdf_path)
                print("⬆︎ PPTX→PDF", rel)

            # STEP ─────────────────────────────────
            elif ext == ".stp":
                base = os.path.splitext(os.path.basename(rel))[0]
                png_name = f"{base}.png"  # saved in CWD
                if stp_to_png(abs_path, png_name):
                    uploads[png_name] = client.files.upload(file=png_name, config={"mime_type": "image/png"})
                    print("⬆︎ STP preview", png_name)
                else:
                    print("[skip] could not render", rel)

            # Unsupported ─────────────────────────
            else:
                print("[skip] unsupported", rel)

        except Exception as exc:
            print(f"[❌] {rel}: {exc}")

    return uploads

# ────────────────────────────────────────────────────────────────
# 4.  Ask Gemini & build HTML
# ────────────────────────────────────────────────────────────────

def generate_html(uploads: dict, repo: str, client):
    if not uploads:
        print("Nothing to analyse → abort.")
        return

    prompt = """
从客户上传的文件中识别每个零件，推断材料、数量及表面处理。

只输出 `<tr>` 表格行，列顺序为：
<tr>
  <td>产品名称</td>
  <td><img …></td>
  <td>材料</td>
  <td>数量</td>
  <td>规格</td>
</tr>

- 产品名称 = STP 文件名去掉后缀
- `<img>` 请引用同名 PNG，写成 `<img src=\"FILE.png\" width=\"120\">`
- 不要输出解释、标题或 ``` 代码块
"""

    parts = [f"Project: {repo}\n"]
    for name, file_obj in uploads.items():
        parts += [f"--- FILE: {name} ---", file_obj, "\n"]
    parts.append(prompt)

    print("📡  Prompting Gemini…")
    try:
        res = client.models.generate_content(model="gemini-2.5-flash", contents=parts)
        rows = res.text.strip()
        if rows.startswith("```"):
            rows = "\n".join(rows.splitlines()[1:-1]).strip()

        with open("template.html", "r", encoding="utf-8") as f:
            html = f.read().replace("{{TABLE_BODY}}", rows)

        out_name = f"{repo}_components.html"
        with open(out_name, "w", encoding="utf-8") as f:
            f.write(html)
        print("✅  HTML written →", out_name)
    except Exception as exc:
        print("[Gemini ❌]", exc)

# ────────────────────────────────────────────────────────────────
# 5.  Entrypoint
# ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    folder = input("📂  Folder to scan → ").strip()
    if not os.path.isdir(folder):
        raise SystemExit("Not a directory.")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise SystemExit("Set GOOGLE_API_KEY.")

    client = genai.Client(api_key=api_key)

    repo_name = os.path.basename(os.path.abspath(folder))
    uploads = upload_files(scan_files(folder), client)
    generate_html(uploads, repo_name, client)
