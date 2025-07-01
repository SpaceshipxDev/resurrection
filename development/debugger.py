import pyvista as pv
import os
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.IFSelect import IFSelect_RetDone

# Define the input STP file and the output PNG file
stp_file = '/Users/hashashin/Documents/grokkk/a260-jl11v-aazj-01.stp' # <-- Change this to your file path
png_file = 'model_snapshot_robust.png'

if not os.path.exists(stp_file):
    print(f"Error: The file '{stp_file}' was not found.")
else:
    try:
        # --- Direct Reading with python-occ-core ---
        print("Reading STP file directly with OCC...")
        step_reader = STEPControl_Reader()
        status = step_reader.ReadFile(stp_file)

        if status != IFSelect_RetDone:
            raise RuntimeError("Error: STEP file could not be read.")

        # Transfer the shapes from the reader
        step_reader.TransferRoots()
        # Get the single resulting shape
        shape = step_reader.OneShape()
        print("STP file read successfully.")

        # --- Visualization with PyVista ---
        # Convert the OCC shape to a PyVista mesh
        # The pv.wrap() function is the magic that connects OCC to PyVista
        mesh = pv.wrap(shape)
        print("Geometry wrapped for PyVista.")

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
        print(f"An error occurred: {e}")