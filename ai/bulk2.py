"""Simple end‑to‑end pipeline
---------------------------------
*   Walk an input folder, find engineering files
*   For every STEP (`.stp`) render an isometric PNG preview **with the same base name**
*   Upload everything to Gemini‑for‑workspace (via `google‑genai`)
*   Ask Gemini to return an HTML table that already embeds the preview images
*   Drop the rows into `template.html`, producing `<repo>_components.html`
    (make sure your template has a column for images)

External requirements  ▸  cadquery, pyvista, pandas, google‑genai, LibreOffice (optional for .pptx ⇒ .pdf)
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
    """Return a list ‹(rel_path, abs_path, ext)› under *root*"""
    out = []
    for dirpath, _, files in os.walk(root):
        for fn in files:
            abs_path = os.path.join(dirpath, fn)
            rel_path = os.path.relpath(abs_path, root)
            out.append((rel_path, abs_path, os.path.splitext(fn)[1].lower()))
    return out

# ────────────────────────────────────────────────────────────────
# 2.  STEP → PNG preview
# ────────────────────────────────────────────────────────────────

def stp_to_png(stp_path: str, png_path: str) -> bool:
    """Render *stp_path* to *png_path* (isometric, 1920×1080)."""
    try:
        shape = cq.importers.importStep(stp_path)
        with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tmp:
            stl_path = tmp.name
        cq.exporters.export(shape, stl_path)

        plotter = pv.Plotter(off_screen=True)
        plotter.add_mesh(pv.read(stl_path), color="tan", show_edges=False)
        plotter.camera_position = "iso"
        plotter.screenshot(png_path, window_size=[1920, 1080])
        plotter.close()
        os.unlink(stl_path)
        return True
    except Exception as exc:
        print(f"[STP→PNG ❌] {stp_path}: {exc}")
        return False

# ────────────────────────────────────────────────────────────────
# 3.  Upload logic
# ────────────────────────────────────────────────────────────────

def upload_files(file_list, client):
    """Upload supported files.

    For every STEP we create & upload a PNG preview (same basename).

    Returns (uploads, preview_paths)
        uploads:        {filename → file_obj}
        preview_paths:  local paths of created PNG previews (for optional later use)
    """
    uploads, preview_paths = {}, []

    for rel, abs_path, ext in file_list:
        try:
            # -------------- PDF --------------
            if ext == ".pdf":
                uploads[rel] = client.files.upload(file=abs_path, config={"mime_type": "application/pdf"})
                print("⬆︎ PDF", rel)

            # -------------- Excel --------------
            elif ext in (".xls", ".xlsx"):
                df = pd.read_excel(abs_path)
                with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
                    csv_path = tmp.name
                df.to_csv(csv_path, index=False)
                uploads[rel] = client.files.upload(file=csv_path, config={"mime_type": "text/csv"})
                os.unlink(csv_path)
                print("⬆︎ Excel→CSV", rel)

            # -------------- PPTX (to PDF) --------------
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

            # -------------- STEP --------------
            elif ext == ".stp":
                base = os.path.splitext(os.path.basename(rel))[0]
                png_name = f"{base}.png"   # preview saved in cwd – keeps things simple
                if stp_to_png(abs_path, png_name):
                    uploads[png_name] = client.files.upload(file=png_name, config={"mime_type": "image/png"})
                    preview_paths.append(png_name)
                    print("⬆︎ STP preview", png_name)
                else:
                    print("[skip] could not render", rel)

            # -------------- Unsupported --------------
            else:
                print("[skip] unsupported", rel)

        except Exception as exc:
            print(f"[❌] {rel}: {exc}")

    return uploads, preview_paths

# ────────────────────────────────────────────────────────────────
# 4.  Ask Gemini & build HTML
# ────────────────────────────────────────────────────────────────

def generate_html(uploads: dict, repo: str, client):
    if not uploads:
        print("Nothing to analyse → abort.")
        return

    prompt = """
从客户上传的文件中，识别每一个零件并推断其材料、数量及表面处理规格。

输出 **仅包含** 表格行（`<tr>`…`</tr>`），列顺序严格如下：
<tr>
    <td>产品名称</td>
    <td>图片</td>
    <td>材料</td>
    <td>数量</td>
    <td>规格</td>
</tr>

- 产品名称 = 对应 STP 文件去掉后缀的文件名
- 图片列请嵌入 `<img src="同名.png" width="160">`
- 不要输出解释、标题、``` 包围块或任何额外内容
"""

    parts = [f"Project: {repo}\n"]
    for name, file_obj in uploads.items():
        parts += [f"--- FILE: {name} ---", file_obj, "\n"]
    parts.append(prompt)

    print("📡  Sending prompt to Gemini…")
    try:
        res = client.models.generate_content(model="gemini-2.5-flash", contents=parts)
        rows = res.text.strip()
        # strip markdown fences if present
        if rows.startswith("```"):
            rows = "\n".join(rows.splitlines()[1:-1]).strip()

        with open("template.html", "r", encoding="utf-8") as f:
            html = f.read().replace("{{TABLE_BODY}}", rows)

        out_name = f"{repo}_components.html"
        with open(out_name, "w", encoding="utf-8") as f:
            f.write(html)
        print("✅  HTML generated →", out_name)
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
    files = scan_files(folder)
    uploads, _previews = upload_files(files, client)
    generate_html(uploads, repo_name, client)
