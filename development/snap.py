import cadquery as cq
from cadquery_png_plugin import export_png   # tiny wrapper around VTK off-screen

shape = cq.importers.importStep("part.stp")
export_png(shape, "preview.png", size=(800, 800))   # returns in <½ s, no window
print("✓ preview.png written")