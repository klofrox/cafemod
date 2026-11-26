"""CafeMice's window: install / remove the mod and start the game, no typing.

Patcher holds the logic (tested); CafeMiceWindow only draws it with tkinter.
Closing the window stops CafeMice (the game then needs the mod removed or
CafeMice started again).
"""

import queue
import sys
import threading
import time
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

BG = "#15181d"
PANEL = "#1d2126"
TEXT = "#e8e8e8"
DIM = "#8a9099"
GOOD = "#4cc38a"
BAD = "#e5636b"
ACCENT = "#f5b828"


class _Lines:
    """stdout replacement: CafeMice's log lines go to the window."""

    def __init__(self, q):
        self.q = q

    def write(self, text):
        if text.strip():
            self.q.put(text.rstrip())

    def flush(self):
        pass


class CafeMiceWindow:
    def __init__(self, patcher):
        import tkinter as tk

        self.tk = tk
        self.p = patcher
        self.lines = queue.Queue()
        sys.stdout = sys.stderr = _Lines(self.lines)

        root = self.root = tk.Tk()
        root.title("CafeMice")
        root.configure(bg=BG)
        root.resizable(False, False)
        root.minsize(390, 0)  # the message below the buttons must not widen it
        icon = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "cafemice.ico"
        if icon.is_file():
            try:
                root.iconbitmap(str(icon))
            except tk.TclError:
                pass

        tk.Label(root, text="CafeMice", bg=BG, fg=ACCENT, font=("Segoe UI", 20, "bold")).pack(pady=(18, 0))
        tk.Label(root, text="Transformice Café modu", bg=BG, fg=DIM, font=("Segoe UI", 10)).pack()

        box = tk.Frame(root, bg=PANEL, padx=18, pady=12)
        box.pack(padx=20, pady=16, fill="x")
        self.mod_label = tk.Label(box, bg=PANEL, font=("Segoe UI", 11), anchor="w")
        self.mod_label.pack(fill="x")
        self.run_label = tk.Label(box, bg=PANEL, font=("Segoe UI", 11), anchor="w")
        self.run_label.pack(fill="x", pady=(4, 0))

        buttons = tk.Frame(root, bg=BG)
        buttons.pack(padx=20, fill="x")
        self.play_btn = self._button(buttons, "▶  Modu kur ve oyna", ACCENT, "#15181d", self.on_play)
        self.play_btn.pack(fill="x")
        self.remove_btn = self._button(buttons, "Modu kaldır", PANEL, TEXT, self.on_remove)
        self.remove_btn.pack(fill="x", pady=(8, 0))

        self.message = tk.Label(root, bg=BG, fg=DIM, font=("Segoe UI", 9), wraplength=340, justify="center")
        self.message.pack(padx=20, pady=(12, 0))
        self.log = tk.Text(root, height=6, width=48, bg=PANEL, fg=DIM, relief="flat", font=("Consolas", 8),
                           state="disabled")
        self.log.pack(padx=20, pady=(8, 18))

        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.refresh()
        root.after(300, self.tick)

    def _button(self, parent, text, bg, fg, command):
        return self.tk.Button(parent, text=text, command=command, bg=bg, fg=fg, activebackground=bg,
                              activeforeground=fg, relief="flat", font=("Segoe UI", 11, "bold"), pady=8,
                              cursor="hand2", borderwidth=0)

    def say(self, text, color=DIM):
        self.message.configure(text=text, fg=color)

    def refresh(self):
        status = self.p.status()
        if status == "no_game":
            self.mod_label.configure(text="●  Transformice bulunamadı (Steam'den kur)", fg=BAD)
        elif status == "installed":
            self.mod_label.configure(text="●  Mod: kurulu", fg=GOOD)
        else:
            self.mod_label.configure(text="●  Mod: kurulu değil", fg=DIM)
        if self.p.running:
            self.run_label.configure(text="●  CafeMice: çalışıyor (bu pencereyi kapatma)", fg=GOOD)
        else:
            self.run_label.configure(text="●  CafeMice: kapalı", fg=DIM)
        self.play_btn.configure(state="disabled" if status == "no_game" else "normal")
        self.remove_btn.configure(state="normal" if status == "installed" else "disabled")

    def on_play(self):
        result = self.p.play()
        if result == "no_game":
            self.say("Önce Transformice'i Steam'den kur.", BAD)
        else:
            self.say("Oyun açılıyor... Oynarken bu pencere açık kalsın (simge durumuna küçültebilirsin).", TEXT)
        self.refresh()

    def on_remove(self):
        if self.p.remove() == "removed":
            self.say("Mod kaldırıldı. Oyun artık Steam'den normal açılır.", TEXT)
        self.refresh()

    def on_close(self):
        if self.p.running and self.p.status() == "installed":
            from tkinter import messagebox
            if not messagebox.askyesno("CafeMice", "CafeMice kapanırsa modlu oyun bağlanamaz.\n\n"
                                                   "Kapatılsın mı? (Oyunu normal oynamak için önce "
                                                   "\"Modu kaldır\"a bas.)"):
                return
        self.root.destroy()

    def tick(self):
        lines = []
        while not self.lines.empty():
            lines.append(self.lines.get_nowait())
        if lines:
            self.log.configure(state="normal")
            for line in lines:
                self.log.insert("end", line + "\n")
            self.log.delete("1.0", "end-200l")
            self.log.see("end")
            self.log.configure(state="disabled")
        if self.p.error == "busy":
            self.say("CafeMice zaten açık: diğer pencereyi kapat, sonra tekrar bas.", BAD)
            self.p.error = "shown"
        elif self.p.error not in (None, "shown"):
            self.say(f"Hata: {self.p.error}", BAD)
            self.p.error = "shown"
        self.refresh()
        self.root.after(500, self.tick)

    def run(self):
        self.root.mainloop()


def main():
    folder = cafe_exe.find_transformice()
    patcher = Patcher(folder=folder, loader=cafe_exe.bundled_loader(), data=cafe_exe.data_dir())
    CafeMiceWindow(patcher).run()
    return 0


if __name__ == "__main__":
    time.sleep(0)
    sys.exit(main())
