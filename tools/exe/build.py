"""Build CafeMice.exe: the Café features alone, for a friend.

    python tools/exe/build.py     # -> dist/CafeMice.exe

Needs PyInstaller (a venv with --system-site-packages is enough) and the
loader built first: python tools/loader/build.py
Nothing of this computer's Café data goes in: only code and the loader SWF.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
LOADER = ROOT / "build" / "TFMProxyLoader_sil.swf"
HERE = Path(__file__).resolve().parent


def main():
    if not LOADER.is_file():
        raise SystemExit(f"{LOADER} is missing: run tools/cafe_sil_loader/build.py first")
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile", "--console", "--name", "CafeMice",
        "--paths", str(ROOT), "--add-data", f"{LOADER};.",
        "--icon", str(HERE / "cafemice.ico"), "--version-file", str(HERE / "version.txt"),
        "--collect-submodules", "caseus", "--hidden-import", "cafemice.cafe_proxy",
        "--exclude-module", "tkinter", "--exclude-module", "pytest", "--exclude-module", "numpy",
        "--exclude-module", "pydantic", "--exclude-module", "pydantic_core",
        "--distpath", str(ROOT / "dist"), "--workpath", str(ROOT / "build" / "pyinstaller"),
        "--specpath", str(ROOT / "build" / "pyinstaller"),
        str(Path(__file__).resolve().parent / "entry.py"),
    ], check=True, cwd=ROOT)
    print(f"built {ROOT / 'dist' / 'CafeMice.exe'}")


if __name__ == "__main__":
    main()
