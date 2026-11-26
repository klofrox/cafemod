"""CafeMice: the Café features alone, as one program for a friend (tools/build_exe.py).

    CafeMice.exe               put the Café loader into Steam's Transformice, run, open the game
    CafeMice.exe --kaldir      put Steam's own Transformice.swf back
    CafeMice.exe --oyunu-acma  run without opening the game (open it yourself)

The loader (build/TFMProxyLoader_sil.swf, bundled in the exe) replaces
Transformice.swf in the Steam folder; Steam's file is kept next to it as
Transformice.swf.orig. The game then connects through this program, which
must be running while playing; it opens the game through Steam itself once
it is listening (steam://rungameid/335240).

The Café proxy (cafe_proxy.py): blocking, favourites,
notes, the archive and search, previews, screenshots, the bell. Its files live
in %APPDATA%\\CafeMice, never next to the exe.
"""

import argparse
import os
import re
import shutil
import socket
import sys
import threading
import time
from pathlib import Path

GAME_FILE = "Transformice.swf"
BACKUP_FILE = "Transformice.swf.orig"
LOADER_NAME = "TFMProxyLoader_sil.swf"
STEAM_APP_ID = 335240
GAME_URL = f"steam://rungameid/{STEAM_APP_ID}"
PROXY_PORT = 11801
STEAM_GUESSES = (Path(r"C:\Program Files (x86)\Steam"), Path(r"C:\Program Files\Steam"))


def _say(text):
    print(text, flush=True)


def data_dir():
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "CafeMice"


def bundled_loader():
    """The loader inside the exe (PyInstaller unpacks it to sys._MEIPASS), or the build output."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / LOADER_NAME
    return Path(__file__).resolve().parent.parent / "build" / LOADER_NAME


def _steam_from_registry():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            return [Path(winreg.QueryValueEx(key, "SteamPath")[0])]
    except OSError:
        return []


def find_transformice(steam_dirs=None):
    """Transformice's folder in any Steam library, or None."""
    steam_dirs = list(steam_dirs) if steam_dirs is not None else _steam_from_registry() + list(STEAM_GUESSES)
    libraries = []
    for steam in steam_dirs:
        libraries.append(Path(steam))
        vdf = Path(steam) / "steamapps" / "libraryfolders.vdf"
        try:
            text = vdf.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for raw in re.findall(r'"path"\s+"([^"]+)"', text):
            libraries.append(Path(raw.replace("\\\\", "\\")))
    for library in libraries:
        folder = library / "steamapps" / "common" / "Transformice"
        if (folder / GAME_FILE).is_file():
            return folder
    return None


def install(folder, loader):
    """Put the loader in place; "installed" or "already". Whatever Steam left
    there (its first file, or an update it put back) becomes the backup."""
    folder = Path(folder)
    game = folder / GAME_FILE
    ours = Path(loader).read_bytes()
    if game.is_file() and game.read_bytes() == ours:
        return "already"
    if game.is_file():
        shutil.copy2(game, folder / BACKUP_FILE)
    game.write_bytes(ours)
    return "installed"


def uninstall(folder):
    """Put Steam's Transformice.swf back; False when there is nothing to undo."""
    folder = Path(folder)
    backup = folder / BACKUP_FILE
    if not backup.is_file():
        return False
    shutil.copy2(backup, folder / GAME_FILE)
    backup.unlink()
    return True


def _port_open(port=PROXY_PORT):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def _wait_and_start(opener=None, tries=120):
    """Open the game through Steam once the proxy listens (the game connects at once)."""
    opener = opener or os.startfile
    for _ in range(tries):
        if _port_open():
            opener(GAME_URL)
            return True
        time.sleep(0.25)
    _say("Proxy açılmadı: oyun başlatılmadı.")
    return False


def start_game_when_ready():
    threading.Thread(target=_wait_and_start, daemon=True).start()


def make_proxy(folder):
    """The Café-only proxy with its files in ``folder``."""
    from .cafe_archive import Archive
    from .cafe_block import Blocklist, Favorites, Notes, Watchlist
    from .cafe_gif import GifAvatars
    from .cafe_proxy import CafeProxy

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    return CafeProxy(
        blocklist=Blocklist(folder / "cafe_blocklist.json"),
        favorites=Favorites(folder / "cafe_favorites.json"),
        watchlist=Watchlist(folder / "cafe_watch.json"),
        notes=Notes(folder / "cafe_notes.json"),
        gifs=GifAvatars(folder / "cafe_gifs.json"),
        archive=Archive(folder / "cafe_archive.sqlite3"),
    )


def _pause():
    if getattr(sys, "frozen", False):
        try:
            input("\nKapatmak için Enter'a bas...")
        except (EOFError, KeyboardInterrupt):  # no console input (started from a script)
            pass


def main(argv=None):
    parser = argparse.ArgumentParser(prog="CafeMice")
    parser.add_argument("--kaldir", action="store_true", help="Steam'in Transformice.swf dosyasını geri koy")
    parser.add_argument("--oyun-klasoru", metavar="KLASOR", help="Transformice'in kurulu olduğu klasör (bulunamazsa)")
    parser.add_argument("--oyunu-acma", action="store_true", help="oyunu açma, sadece CafeMice'i çalıştır")
    args = parser.parse_args(argv)

    folder = Path(args.oyun_klasoru) if args.oyun_klasoru else find_transformice()
    if folder is None:
        _say("Steam'de Transformice bulunamadı. Transformice'i Steam'den kur, ya da klasörünü ver:\n"
             '  CafeMice.exe --oyun-klasoru "D:\\SteamLibrary\\steamapps\\common\\Transformice"')
        _pause()
        return 1

    if args.kaldir:
        if uninstall(folder):
            _say(f"Steam'in kendi Transformice dosyası geri kondu ({folder}). Oyun artık normal açılır.")
        else:
            _say("Kaldırılacak bir şey yok: oyun zaten normal.")
        _pause()
        return 0

    try:
        state = install(folder, bundled_loader())
    except PermissionError:
        _say("Oyun dosyası değiştirilemedi: Transformice açıksa kapat, sonra tekrar dene.")
        _pause()
        return 1
    if state == "installed":
        _say(f"Café yükleyicisi kuruldu ({folder}). Orijinali {BACKUP_FILE} olarak saklandı.")
    if args.oyunu_acma:
        _say("CafeMice çalışıyor. Şimdi Transformice'i Steam'den aç.")
    else:
        _say("CafeMice çalışıyor, Transformice Steam'den açılıyor...")
        start_game_when_ready()
    _say("Oynarken bu pencere açık kalmalı. Normal oyuna dönmek için: CafeMice.exe --kaldir")
    _say(f"Veriler: {data_dir()}\n")
    try:
        make_proxy(data_dir()).run()
    except OSError as exc:
        if getattr(exc, "errno", None) in (10048, 98, 48) or getattr(exc, "winerror", None) == 10048:
            _say("CafeMice zaten açık (ya da başka bir proxy 11801 portunu kullanıyor). Açık olanı kapat, tekrar dene.")
            _pause()
            return 1
        raise
    return 0


if __name__ == "__main__":
    sys.exit(main())
