import trimesh
mesh = trimesh.load("part.stl")

# Save PNG snapshot (returns PNG bytes)
png_bytes = mesh.scene().save_image(resolution=(800,800))
with open("preview.png", "wb") as f:
    f.write(png_bytes)

print("✓ preview.png written")