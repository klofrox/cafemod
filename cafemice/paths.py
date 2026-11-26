"""Where CafeMice keeps its files: %APPDATA%\\CafeMice (never next to the code)."""
import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("APPDATA") or Path.home()) / "CafeMice"
