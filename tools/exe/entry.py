"""PyInstaller entry for CafeMice.exe: the window, or the command line with arguments."""
import os
import sys

if sys.stdout is None:  # a window app has no console: options still work, quietly
    sys.stdout = sys.stderr = open(os.devnull, "w", encoding="utf-8")

if len(sys.argv) > 1:
    from cafemice.launcher import main
else:
    from cafemice.gui import main

if __name__ == "__main__":
    sys.exit(main())
