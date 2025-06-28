import sys

# Usage: freecadcmd export_stp_to_png.py in.stp out.png

stp_path = sys.argv[1]
png_path = sys.argv[2]

import FreeCAD
import ImportGui

doc = FreeCAD.newDocument()
ImportGui.insert(stp_path, doc.Name)
view = FreeCAD.Gui.activeDocument().activeView()
view.viewAxonometric()
view.fitAll()
view.saveImage(png_path, 800, 600, 'White')