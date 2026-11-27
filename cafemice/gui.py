"""CafeMice's window: install / remove the mod and start the game, no typing.

Patcher holds the logic (tested); CafeMiceWindow only draws it with tkinter.
Minimising or closing the window puts it in the tray (next to the clock):
CafeMice keeps running; the tray icon's menu opens it, removes the mod or
stops CafeMice (the game then needs the mod removed or CafeMice started again).
"""

import queue
import sys
import threading
from pathlib import Path

from . import launcher as cafe_exe


class Patcher:
    """Install / remove the loader and run the Café proxy in the background."""

    def __init__(self, *, folder, loader, data, make_proxy=cafe_exe.make_proxy,
                 start_thread=None, open_game=None):
        self.folder = Path(folder) if folder else None
        self.loader = Path(loader)
        self.data = Path(data)
        self._make_proxy = make_proxy
        self._start_thread = start_thread or (lambda fn: threading.Thread(target=fn, daemon=True).start())
        self._open_game = open_game or (lambda: self._start_thread(cafe_exe._wait_and_start))
        self.running = False
        self.error = None

    def status(self):
        """"no_game", "installed" or "not_installed"."""
        if self.folder is None or not (self.folder / cafe_exe.GAME_FILE).is_file():
            return "no_game"
        game = (self.folder / cafe_exe.GAME_FILE).read_bytes()
        return "installed" if game == self.loader.read_bytes() else "not_installed"

    def _run_proxy(self):
        try:
            self._make_proxy(self.data).run()
        except OSError as exc:
            if getattr(exc, "errno", None) in (10048, 98, 48) or getattr(exc, "winerror", None) == 10048:
                self.error = "busy"
            else:
                self.error = str(exc)
        except Exception as exc:  # shown in the window, never a crash
            self.error = str(exc)
        finally:
            self.running = False

    def play(self):
        """Install if needed, start CafeMice once, open the game."""
        if self.status() == "no_game":
            return "no_game"
        cafe_exe.install(self.folder, self.loader)
        if not self.running:
            self.running = True
            self.error = None
            self._start_thread(self._run_proxy)
        if self.error is None:
            self._open_game()
        return "ok"

    def remove(self):
        """Put Steam's own Transformice.swf back: "removed" or "nothing"."""
        if self.folder is None:
            return "nothing"
        return "removed" if cafe_exe.uninstall(self.folder) else "nothing"


# --- the window ------------------------------------------------------------------
#
# Plain and dark (#0f0f0f), in Outfit (bundled from fonts/, SIL Open Font License).

BG = "#0f0f0f"
CARD = "#171717"
LINE = "#262626"
TEXT = "#f2f2f2"
MUTED = "#8c8c8c"
ACCENT = "#f5b828"
ACCENT_HOVER = "#ffc94a"
GOOD = "#4ade80"
BAD = "#f87171"


def _fonts_dir():
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "fonts"


def _icon_path():
    """The exe carries the icon next to its files; from source it is in tools/exe."""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "cafemice.ico"
    return Path(__file__).resolve().parent.parent / "tools" / "exe" / "cafemice.ico"


def _load_fonts():
    """Make the bundled Outfit files usable by Tk, for this process only."""
    try:
        import ctypes
        for f in _fonts_dir().glob("*.ttf"):
            ctypes.windll.gdi32.AddFontResourceExW(str(f), 0x10, 0)  # FR_PRIVATE
    except (OSError, AttributeError):
        pass  # not Windows: Tk falls back to its own font


class CafeMiceWindow:
    def __init__(self, patcher):
        import tkinter as tk

        _load_fonts()
        self.tk = tk
        self.p = patcher
        root = self.root = tk.Tk()
        root.title("CafeMice")
        root.configure(bg=BG)
        root.resizable(False, False)
        icon = _icon_path()
        if icon.is_file():
            try:
                root.iconbitmap(str(icon))
            except tk.TclError:
                pass

        body = tk.Frame(root, bg=BG, padx=28, pady=26)
        body.pack()
        tk.Label(body, text="CafeMice", bg=BG, fg=TEXT, font=("Outfit", 26, "bold")).pack(anchor="w")
        tk.Label(body, text="Transformice Café modu", bg=BG, fg=MUTED,
                 font=("Outfit Medium", 11)).pack(anchor="w", pady=(0, 18))

        card = tk.Frame(body, bg=CARD, highlightbackground=LINE, highlightthickness=1, padx=16, pady=12)
        card.pack(fill="x")
        self.mod_label = tk.Label(card, bg=CARD, font=("Outfit Medium", 12), anchor="w")
        self.mod_label.pack(fill="x")
        self.run_label = tk.Label(card, bg=CARD, font=("Outfit Medium", 12), anchor="w")
        self.run_label.pack(fill="x", pady=(4, 0))

        self.play_btn = self._button(body, "Modu kur ve oyna", ACCENT, ACCENT_HOVER, "#111111", self.on_play)
        self.play_btn.pack(fill="x", pady=(18, 0))
        self.remove_btn = self._button(body, "Modu kaldır", CARD, "#202020", TEXT, self.on_remove, border=True)
        self.remove_btn.pack(fill="x", pady=(10, 0))

        self.message = tk.Label(body, bg=BG, fg=MUTED, font=("Outfit Medium", 10), wraplength=300,
                                justify="left", anchor="w")
        self.message.pack(fill="x", pady=(14, 0))

        # Tray menu clicks come from the tray's own thread: Tk runs them here.
        self.calls = queue.Queue()
        self.tray = self._make_tray()
        root.protocol("WM_DELETE_WINDOW", self.on_x)
        root.bind("<Unmap>", self._on_unmap)
        self.refresh()
        root.after(500, self.tick)
        root.after(100, self._run_calls)

    # --- tray --------------------------------------------------------------------

    def _make_tray(self):
        """The tray icon, or None when pystray is not there (the window then
        behaves as before: minimise to the taskbar, close stops CafeMice)."""
        try:
            import pystray
            from PIL import Image
            image = Image.open(_icon_path())
        except Exception:
            return None
        later = self.calls.put
        menu = pystray.Menu(
            pystray.MenuItem("Aç", lambda: later(self.show), default=True),
            pystray.MenuItem("Modu kaldır", lambda: later(self.on_remove),
                             enabled=lambda item: self.p.status() == "installed"),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Kapat", lambda: later(self.on_close)),
        )
        icon = pystray.Icon("CafeMice", image, "CafeMice", menu)
        try:
            icon.run_detached()
        except Exception:
            return None
        return icon

    def _run_calls(self):
        while True:
            try:
                call = self.calls.get_nowait()
            except queue.Empty:
                break
            call()
        if self.root.winfo_exists():
            self.root.after(100, self._run_calls)

    def _on_unmap(self, event):
        # Minimised: off the taskbar, into the tray.
        if self.tray and event.widget is self.root and self.root.state() == "iconic":
            self.root.after(0, self.to_tray)

    def on_x(self):
        """The window's X: to the tray while CafeMice runs, else close."""
        if self.tray and self.p.running:
            self.to_tray()
        else:
            self.on_close()

    def to_tray(self):
        self.root.withdraw()

    def show(self):
        self.root.deiconify()
        self.root.state("normal")
        self.root.lift()
        self.root.focus_force()

    def _button(self, parent, text, bg, hover, fg, command, border=False):
        tk = self.tk
        b = tk.Label(parent, text=text, bg=bg, fg=fg, font=("Outfit SemiBold", 13), pady=11, width=24,
                     cursor="hand2", highlightthickness=1 if border else 0, highlightbackground=LINE)
        b.enabled = True
        b.colors = (bg, hover, fg)
        b.bind("<Enter>", lambda e: b.enabled and b.configure(bg=hover))
        b.bind("<Leave>", lambda e: b.enabled and b.configure(bg=bg))
        b.bind("<ButtonRelease-1>", lambda e: b.enabled and command())
        return b

    def _enable(self, b, on):
        b.enabled = on
        bg, _, fg = b.colors
        b.configure(bg=bg if on else CARD, fg=fg if on else "#4a4a4a", cursor="hand2" if on else "")

    def say(self, text, color=MUTED):
        self.message.configure(text=text, fg=color)

    def refresh(self):
        status = self.p.status()
        if status == "no_game":
            self.mod_label.configure(text="●  Transformice bulunamadı", fg=BAD)
        elif status == "installed":
            self.mod_label.configure(text="●  Mod kurulu", fg=GOOD)
        else:
            self.mod_label.configure(text="●  Mod kurulu değil", fg=MUTED)
        if self.p.running:
            self.run_label.configure(text="●  CafeMice çalışıyor", fg=GOOD)
        else:
            self.run_label.configure(text="●  CafeMice kapalı", fg=MUTED)
        self._enable(self.play_btn, status != "no_game")
        self._enable(self.remove_btn, status == "installed")

    def on_play(self):
        if self.p.play() == "no_game":
            self.say("Önce Transformice'i Steam'den kur.", BAD)
        else:
            self.say("Oyun açılıyor. Oynarken CafeMice açık kalsın: küçültünce saatin yanındaki "
                     "simgeye iner, sağ tıkla kapatırsın.")
        self.refresh()

    def on_remove(self):
        if self.p.remove() == "removed":
            self.say("Mod kaldırıldı. Oyun Steam'den normal açılır.")
        self.refresh()

    def on_close(self):
        if self.p.running and self.p.status() == "installed":
            from tkinter import messagebox
            if not messagebox.askyesno("CafeMice", "CafeMice kapanırsa modlu oyun bağlanamaz.\n\n"
                                                   "Kapatılsın mı? (Oyunu normal oynamak için önce "
                                                   "\"Modu kaldır\"a bas.)"):
                return
        if self.tray:
            self.tray.stop()
        self.root.destroy()

    def tick(self):
        if self.p.error == "busy":
            self.say("CafeMice zaten açık: diğer pencereyi kapat, sonra tekrar bas.", BAD)
            self.p.error = "shown"
        elif self.p.error not in (None, "shown"):
            self.say(f"Hata: {self.p.error}", BAD)
            self.p.error = "shown"
        self.refresh()
        if self.tray:
            self.tray.update_menu()
        self.root.after(500, self.tick)

    def run(self):
        self.root.mainloop()


def main():
    if sys.stdout is None:  # a window app: CafeMice's log lines go nowhere
        import os
        sys.stdout = sys.stderr = open(os.devnull, "w", encoding="utf-8")
    folder = cafe_exe.find_transformice()
    patcher = Patcher(folder=folder, loader=cafe_exe.bundled_loader(), data=cafe_exe.data_dir())
    CafeMiceWindow(patcher).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
