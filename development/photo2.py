import numpy as np
from stl import mesh
from mpl_toolkits import mplot3d
from matplotlib import pyplot

# --- Configuration ---
STL_FILE = 'part.stl'
OUTPUT_IMAGE = 'stl_image_matplotlib.png'

# --- Main Script ---

# Create a new figure
figure = pyplot.figure()
axes = figure.add_subplot(111, projection='3d')

# Load the STL file and add the vectors to the plot
try:
    your_mesh = mesh.Mesh.from_file(STL_FILE)
except FileNotFoundError:
    print(f"Error: The file '{STL_FILE}' was not found.")
    print("Please make sure the STL file is in the same directory as the script.")
    exit()

# The stl library adds the vectors to the axes
# Matplotlib requires a list of vectors, so we just grab all the vectors
# from the mesh.
axes.add_collection3d(mplot3d.art3d.Poly3DCollection(your_mesh.vectors))

# Auto-scale to the mesh's size
scale = your_mesh.points.flatten()
axes.auto_scale_xyz(scale, scale, scale)

# Set the viewing angle (elevation, azimuth)
axes.view_init(elev=20., azim=30)

# Set labels (optional)
axes.set_xlabel('X')
axes.set_ylabel('Y')
axes.set_zlabel('Z')

# Save the plot to a file
print(f"Saving image to {OUTPUT_IMAGE}...")
pyplot.savefig(OUTPUT_IMAGE, dpi=300) # Use a high DPI for better quality

print("Done.")
# To show the plot interactively (optional)
# pyplot.show()