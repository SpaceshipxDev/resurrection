import pyvista as pv
import os

# Define the input STP file and the output PNG file
stp_file = '/Users/hashashin/Documents/grokkk/a260-jl11v-aazj-01.stp' # <-- Change this to your file path
png_file = 'model_snapshot.png'

# --- Safety Check ---
if not os.path.exists(stp_file):
    print(f"Error: The file '{stp_file}' was not found.")
else:
    try:
        # Read the STP file
        mesh = pv.read(stp_file)

        # Create a plotter object without a pop-up window
        plotter = pv.Plotter(off_screen=True)

        # Add the mesh to the plotter
        plotter.add_mesh(mesh, color='lightblue', show_edges=True)

        # Set a nice isometric camera view
        plotter.camera_position = 'iso' 

        # Save the screenshot
        plotter.screenshot(png_file)

        print(f"Successfully saved snapshot to {png_file}")

    except Exception as e:
        print(f"An error occurred while processing the file with PyVista: {e}")