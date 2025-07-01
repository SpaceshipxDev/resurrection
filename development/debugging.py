import pyvista as pv

mesh = pv.read('development/part.stl')
plotter = pv.Plotter()
plotter.add_mesh(mesh, color='tan', show_edges=True)
plotter.camera_position = 'iso'
plotter.show()