import pyvista as pv

mesh = pv.read('/Users/hashashin/Documents/grokkk/generated_stl/a260-jl11v-aazj-01.stl')
plotter = pv.Plotter()
plotter.add_mesh(mesh, color='tan', show_edges=True)
plotter.camera_position = 'iso'
plotter.show()