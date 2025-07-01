# verify_env.py
import sys

print(f"Python Executable: {sys.executable}")
print("-" * 20)

try:
    import pyvista
    print("SUCCESS: PyVista is installed and importable.")
except ImportError as e:
    print(f"ERROR: Could not import PyVista. {e}")

try:
    # This is the core library provided by pythonocc-core
    from OCC.Core.BRep import BRep_Builder
    print("SUCCESS: pythonocc-core (OCC.Core) is installed and importable.")
except ImportError as e:
    print(f"ERROR: Could not import pythonocc-core. {e}")