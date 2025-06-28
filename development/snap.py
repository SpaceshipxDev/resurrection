import cadquery as cq
shape = cq.importers.importStep("/Users/hashashin/Downloads/A260兼容吉利11V3.0侧视100度载具2D/qjr-aamk-09b-04.stp")
cq.exporters.export(shape, 'part.stl')