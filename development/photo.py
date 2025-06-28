import cadquery as cq
import cadquery_png_plugin.plugin   #  ⚠️  MUST be imported once!

model = cq.importers.importStep("/Users/hashashin/Downloads/A260兼容吉利11V3.0侧视100度载具2D/qjr-aamk-09b-03.stp")     # read STEP
assy  = cq.Assembly(model)                         # plugin works on assemblies

assy.exportPNG(                                     # no window, no block
    file_path="preview.png",
    options={
        "width": 800,
        "height": 800,
        "view": "front-top-right",   # pick any: front, left, iso, etc.
        "zoom": 1.2,                 # optional
        "color_theme": "default"     # or "black_and_white"
    }
)
print("✓ preview.png written")