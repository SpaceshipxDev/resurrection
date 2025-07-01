import pyvista as pv

STL_FILE= "/Users/hashashin/Documents/grokkk/generated_stl/a260-jl11v-aazj-01.stl"
OUTPUT_IMAGE="printed.png"
plotter = pv.Plotter(off_screen=True) 
mesh = pv.read(STL_FILE) 
plotter.add_mesh(mesh, color="tan", show_edges=False) 
plotter.camera_position="iso" 
plotter.screenshot(OUTPUT_IMAGE, window_size=[1920, 1080])

plotter.close() 
