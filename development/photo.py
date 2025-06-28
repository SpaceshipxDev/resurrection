import cadquery as cq, trimesh, pathlib, pyglet
pyglet.options["headless"] = True               # no window at all

cq.importers.importStep("/Users/hashashin/Downloads/A260兼容吉利11V3.0侧视100度载具2D/qjr-aamk-09b-03.stp").export("tmp.stl")   # STEP → STL

scene = trimesh.load("tmp.stl")
png   = scene.save_image(resolution=(800, 800))         # off-screen framebuffer
pathlib.Path("preview.png").write_bytes(png)
print("✓ preview.png written with trimesh")