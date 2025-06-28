import cadquery as cq
from cadquery.vis import show     # lightweight VTK viewer

step_path = "/Users/hashashin/Downloads/A260兼容吉利11V3.0侧视100度载具2D/qjr-aamk-09b-04.stp"            # ← your STEP file
shape     = cq.importers.importStep(step_path)   # read STEP  [oai_citation:0‡cadquery.readthedocs.io](https://cadquery.readthedocs.io/en/latest/importexport.html)

# This opens NO GUI and writes an 800×800 PNG
show(
    shape,
    width=800,
    height=800,
    screenshot="preview.png",
    interact=False               # headless → just render & quit
)                                #  [oai_citation:1‡cadquery.readthedocs.io](https://cadquery.readthedocs.io/en/latest/vis.html)