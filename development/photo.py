import cadquery as cq
m = cq.importers.importStep("/Users/hashashin/Downloads/A260兼容吉利11V3.0侧视100度载具2D/qjr-aamk-09b-03.stp")
print("solids:", len(m.solids()))          # should be > 0
print("bbox  :", m.val().BoundingBox())    # should be non-zero size
