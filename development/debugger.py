import pyvista as pv
import os
import numpy as np

# --- Import necessary OCC libraries ---
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_SOLID
from OCC.Core.TopoDS import topods
from OCC.Core.BRep import BRep_Tool
from OCC.Core.TopLoc import TopLoc_Location

# Define the input STP file and the output PNG file
stp_file = '/Users/hashashin/Documents/grokkk/a260-jl11v-aazj-01.stp' # <-- Change this to your file path
png_file = 'model_snapshot_final.png'

# --- Safety Check ---
if not os.path.exists(stp_file):
    print(f"Error: The file '{stp_file}' was not found.")
else:
    try:
        # --- 1. Direct Reading with python-occ-core ---
        print("Reading STP file directly with OCC...")
        step_reader = STEPControl_Reader()
        status = step_reader.ReadFile(stp_file)

        if status != IFSelect_RetDone:
            raise RuntimeError("Error: STEP file could not be read.")

        step_reader.TransferRoots()
        shape = step_reader.OneShape()
        print("STP file read successfully.")

        # --- 2. Tessellate the Shape into a Mesh ---
        # This is the crucial new step. We convert the mathematical solid into triangles.
        print("Tessellating shape into a mesh...")

        # The 'deflection' parameter controls mesh quality.
        # Lower numbers = higher quality = more triangles. 0.1 is a good starting point.
        linear_deflection = 0.1
        angular_deflection = 0.5
        BRepMesh_IncrementalMesh(shape, linear_deflection, False, angular_deflection, True)

        # --- 3. Extract vertices and faces for PyVista ---
        vertices = []
        faces = []
        vertex_offset = 0

        # Use an explorer to iterate over all faces in the shape
        explorer = TopExp_Explorer(shape, TopAbs_FACE)
        while explorer.More():
            face = explorer.Current()
            location = TopLoc_Location()
            triangulation = BRep_Tool.Triangulation(face, location)

            if triangulation is None:
                explorer.Next()
                continue
                
            # Get the 3D points (vertices) of the face
            nodes = triangulation.Nodes()
            # Transform vertices to global coordinates
            trsf = location.Transformation()
            
            for i in range(1, nodes.Length() + 1):
                p = nodes.Value(i)
                p.Transform(trsf)
                vertices.append([p.X(), p.Y(), p.Z()])

            # Get the triangles of the face
            triangles = triangulation.Triangles()
            for i in range(1, triangles.Length() + 1):
                triangle = triangles.Value(i)
                # Get the vertex indices for the triangle
                v1, v2, v3 = triangle.Get()
                # Add the face to the list, with the leading '3' for PyVista
                # and offsetting indices for this new face
                faces.extend([3, v1 - 1 + vertex_offset, v2 - 1 + vertex_offset, v3 - 1 + vertex_offset])
            
            vertex_offset += nodes.Length()
            explorer.Next()

        print(f"Mesh extracted: {len(vertices)} vertices, {len(faces)//4} faces.")

        # --- 4. Create PyVista Mesh and Plot ---
        # Create the mesh object from our extracted data
        mesh = pv.PolyData(np.array(vertices), np.array(faces))
        print("PyVista mesh created successfully.")

        # Create a plotter object without a pop-up window
        plotter = pv.Plotter(off_screen=True)
        
        # Add the mesh to the plotter with some nice rendering settings
        plotter.add_mesh(mesh, color='lightblue', show_edges=True, edge_color='gray', lighting=True, specular=0.5, specular_power=15)
        
        # Set a clean background
        plotter.set_background('white')
        
        # Set camera to a standard isometric view and zoom to fit
        plotter.view_isometric()
        plotter.camera.zoom(0.9) # Zoom out slightly to avoid clipping edges

        # Take a high-resolution screenshot
        plotter.screenshot(png_file, window_size=[1920, 1080])

        print(f"Successfully saved snapshot to {png_file}")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"An error occurred: {e}")