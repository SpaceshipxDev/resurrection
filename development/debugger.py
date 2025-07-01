import trimesh

# Define the input STP file and the output PNG file
stp_file = '/Users/hashashin/Documents/grokkk/a260-jl11v-aazj-01.stp' # <-- Change this to your file path
png_file = 'nuk.png'

# 1. Load the STP file
# Trimesh automatically creates a scene with all the bodies from the file
scene = trimesh.load(stp_file)

# 2. Save a snapshot of the scene
# The resolution of the output image can be specified.
# The scene will be automatically oriented to fit in the frame.
png_data = scene.save_image(resolution=(800, 600))

# 3. Write the data to a file
with open(png_file, 'wb') as f:
    f.write(png_data)

print(f"Successfully saved snapshot to {png_file}")