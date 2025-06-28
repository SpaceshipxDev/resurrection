import pyvista as pv

# --- Configuration ---
STL_FILE = 'part.stl'
OUTPUT_IMAGE = 'stl_image_pyvista.png'

# --- Main Script ---

# Set up the plotter. The `off_screen` argument is crucial for saving
# a screenshot without popping up an interactive window.
plotter = pv.Plotter(off_screen=True)

# Load the STL file
try:
    mesh = pv.read(STL_FILE)
except FileNotFoundError:
    print(f"Error: The file '{STL_FILE}' was not found.")
    print("Please make sure the STL file is in the same directory as the script.")
    exit()

# Add the mesh to the plotter
# You can customize the color, style, etc.
# For example: color='lightblue', style='surface', show_edges=True
plotter.add_mesh(mesh, color='tan', show_edges=False)

# --- Camera Position (VERY USEFUL!) ---
# You can set the camera position to get the perfect angle.
# 'cpos' can be a string ('xy', 'yz', etc.) or a list of vectors.
# Find the best camera angle interactively first by removing `off_screen=True`
# and `plotter.screenshot()`, and adding `plotter.show()`. Then press 'c'
# to print the camera position to the console and paste it here.
# Example custom camera position:
# plotter.camera_position = [(150, 90, 100), (-5, 10, 20), (0, 1, 0)]

# Or use a standard view
plotter.camera_position = 'iso' # Isometric view

# You can also add lighting features if desired
# plotter.enable_shadows()

# Take the screenshot and save it
print(f"Saving image to {OUTPUT_IMAGE}...")
plotter.screenshot(OUTPUT_IMAGE, window_size=[1920, 1080]) # High resolution

# Close the plotter
plotter.close()

print("Done.")