"""
STEP ➜ off-screen PNG snapshot
--------------------------------
Requires:
    conda install -c conda-forge cadquery pyvista
or
    pip install cadquery pyvista

Tested on macOS 14 (Apple M-series) + Python 3.12
"""

import cadquery as cq
import pyvista as pv
import numpy as np
import os
import sys

# ========= CONFIG =========
STP_FILE = "/Users/hashashin/Documents/grokkk/a260-jl11v-aazj-01.stp"   # <-- change path
PNG_FILE = "model_snapshot_final.png"
TESSELLATION_ACCURACY = 0.1   # mm; smaller = finer mesh
WINDOW_SIZE = (1920, 1080)
# ==========================

# --- basic sanity check ---
if not os.path.exists(STP_FILE):
    sys.exit(f"ERROR: file not found → {STP_FILE}")

print("🔄  Loading STEP with CadQuery …")
shape_or_wp = cq.importers.importStep(STP_FILE)

# CadQuery returns either a Workplane or a plain Shape.  Extract a Shape:
if isinstance(shape_or_wp, cq.Workplane):
    occt_shape = cq.Compound.makeCompound([s.val() for s in shape_or_wp.solids()])
else:
    occt_shape = shape_or_wp  # already a Shape/Compound

print("🔄  Tessellating …")
# Tessellate once; returns (vertices, triangles) lists
verts, tris = occt_shape.tessellate(TESSELLATION_ACCURACY)

# --- build a PyVista PolyData ---
vertices = np.asarray(verts, dtype=np.float64)

# PyVista wants a flat array whose layout is: [N, i0, i1, i2,  N, i0, i1, i2, …]
faces = np.hstack(
    [
        np.full((len(tris), 1), 3, dtype=np.int64),      # leading "3" = triangle
        np.asarray(tris, dtype=np.int64)
    ]
).flatten()

mesh = pv.PolyData(vertices, faces)
print(f"   ➜ Mesh: {len(vertices)} vertices, {len(tris)} triangles")

print("🎨  Rendering off-screen …")
plotter = pv.Plotter(off_screen=True, window_size=WINDOW_SIZE)
plotter.add_mesh(
    mesh,
    color="lightblue",
    show_edges=True,
    edge_color="gray",
    lighting=True,
    specular=0.5,
    specular_power=15,
)
plotter.set_background("white")
plotter.view_isometric()
plotter.camera.zoom(0.9)
plotter.screenshot(PNG_FILE)

print(f"✅  Snapshot saved → {os.path.abspath(PNG_FILE)}")