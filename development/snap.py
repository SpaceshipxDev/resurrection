import sys

# Usage: freecadcmd export_stp_to_png.py input.stp output.png

infile, outfile = sys.argv[1], sys.argv[2]

import FreeCAD
import ImportGui

doc = FreeCAD.newDocument()
ImportGui.insert(infile, doc.Name)

# Only works with GUI module loaded (possible in FreeCAD 0.20+ on Mac!)
import FreeCADGui
FreeCADGui.showMainWindow()
view = FreeCADGui.activeDocument().activeView()
view.viewAxonometric()
view.fitAll()
view.saveImage(outfile, 1024, 768, 'White')

FreeCAD.closeDocument(doc.Name)
FreeCADGui.getMainWindow().close()