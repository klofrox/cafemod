"""CafeMice's window: install / remove the mod and start the game, no typing.

Patcher holds the logic (tested); CafeMiceWindow only draws it with tkinter.
Closing the window stops CafeMice (the game then needs the mod removed or
CafeMice started again).
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
# Drawn here, in the game's spirit (wood frame, parchment, wooden buttons); no
# picture of the game is bundled. The mouse in the header is the game's own
# icon, read from this player's Steam folder (icones/128.png) when it is there.

W, H = 420, 560
WOOD = (110, 70, 38)
WOOD_DARK = (74, 45, 22)
WOOD_LIGHT = (140, 92, 52)
PARCHMENT = (246, 228, 186)
PARCHMENT_EDGE = (150, 104, 56)
INK = (70, 44, 20)
INK_DIM = (128, 98, 66)
GREEN = (98, 170, 58)
GREEN_DARK = (52, 104, 28)
GOOD = "#3f8f2a"
BAD = "#b8372d"
DIM = "#80684a"
TEXT_INK = "#46301a"
TITLE = (255, 214, 92)


def _font(size, bold=True):
    from PIL import ImageFont
    names = ("seguibl.ttf", "segoeuib.ttf", "arialbd.ttf") if bold else ("segoeui.ttf", "arial.ttf")
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wood(size, seed=7):
    """Vertical wooden planks with grain, as a PIL image."""
    import random
    from PIL import Image, ImageDraw
    w, h = size
    img = Image.new("RGB", size, WOOD)
    d = ImageDraw.Draw(img)
    rng = random.Random(seed)
    x = 0
    while x < w:
        plank = rng.randint(54, 78)
        shade = rng.randint(-12, 12)
        base = tuple(max(0, min(255, c + shade)) for c in WOOD)
        d.rectangle((x, 0, x + plank, h), fill=base)
        for _ in range(9):  # grain
            gx = x + rng.randint(4, plank - 4)
            tone = tuple(max(0, c - rng.randint(10, 22)) for c in base)
            d.line([(gx + rng.randint(-2, 2), y) for y in range(0, h + 40, 40)], fill=tone, width=1)
        d.line((x, 0, x, h), fill=WOOD_DARK, width=2)  # gap between planks
        d.line((x + 2, 0, x + 2, h), fill=WOOD_LIGHT, width=1)
        x += plank
    return img


def _outlined(draw, xy, text, font, fill, outline, width=3, anchor="mm"):
    x, y = xy
    for dx in range(-width, width + 1):
        for dy in range(-width, width + 1):
            if dx * dx + dy * dy <= width * width:
                draw.text((x + dx, y + dy), text, font=font, fill=outline, anchor=anchor)
    draw.text((x, y), text, font=font, fill=fill, anchor=anchor)


def _background(mouse=None):
    from PIL import Image, ImageDraw
    img = _wood((W, H))
    d = ImageDraw.Draw(img)
    # Frame: a darker border with a light inner edge, like a wooden board.
    d.rectangle((0, 0, W - 1, H - 1), outline=WOOD_DARK, width=8)
    d.rectangle((8, 8, W - 9, H - 9), outline=WOOD_LIGHT, width=2)
    header_y = 70
    if mouse is not None:
        m = mouse.convert("RGBA").resize((96, 96))
        img.paste(m, (24, header_y - 48), m)
        title_x = 260
    else:
        title_x = W // 2
    _outlined(d, (title_x, header_y - 10), "CafeMice", _font(40), TITLE, WOOD_DARK, width=3)
    _outlined(d, (title_x, header_y + 26), "Transformice Café modu", _font(14, bold=False), (250, 238, 210),
              WOOD_DARK, width=2)
    # Parchment panel for the state.
    d.rounded_rectangle((26, 138, W - 26, 250), radius=16, fill=PARCHMENT, outline=PARCHMENT_EDGE, width=4)
    d.rounded_rectangle((34, 146, W - 34, 242), radius=12, outline=(232, 208, 160), width=2)
    # Parchment for the message and the log.
    d.rounded_rectangle((26, 404, W - 26, H - 24), radius=14, fill=PARCHMENT, outline=PARCHMENT_EDGE, width=3)
    return img


def _button(text, kind, state, arrow=False):
    """A wooden (or green) button image: state is normal, hover, pressed or disabled."""
    from PIL import Image, ImageDraw
    w, h = W - 52, 58
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if kind == "green":
        face, dark = GREEN, GREEN_DARK
    else:
        face, dark = (172, 116, 64), (96, 58, 26)
    if state == "hover":
        face = tuple(min(255, c + 22) for c in face)
    if state == "disabled":
        face, dark = (150, 130, 110), (100, 86, 72)
    drop = 2 if state == "pressed" else 6
    top = 4 if state == "pressed" else 0
    d.rounded_rectangle((0, drop, w - 1, h - 1), radius=16, fill=dark)  # the edge below
    d.rounded_rectangle((0, top, w - 1, h - 1 - drop + top), radius=16, fill=face, outline=dark, width=3)
    d.rounded_rectangle((8, top + 6, w - 9, top + (h - drop) // 2), radius=10,
                        fill=tuple(min(255, c + 30) for c in face))  # shine
    color = (255, 255, 255) if state != "disabled" else (220, 210, 200)
    cy = top + (h - drop) // 2 + 1
    cx = w // 2
    if arrow:  # a play triangle, drawn (fonts may lack the symbol)
        font = _font(19)
        half = (d.textlength(text, font=font) + 30) / 2
        ax = cx - half
        tri = [(ax, cy - 9), (ax + 16, cy), (ax, cy + 9)]
        d.polygon([(x + 2, y + 2) for x, y in tri], fill=dark)
        d.polygon(tri, fill=color, outline=dark)
        cx += 15
    _outlined(d, (cx, cy), text, _font(19), color, dark, width=2)
    return img


class _Lines:
    """stdout replacement: CafeMice's log lines go to the window."""

    def __init__(self, q):
        self.q = q

    def write(self, text):
        if text.strip():
            self.q.put(text.rstrip())

    def flush(self):
        pass


def _game_icon(folder):
    """The game's own icon from this player's Steam folder, or None."""
    if folder is None:
        return None
    from PIL import Image
    try:
        return Image.open(Path(folder) / "icones" / "128.png")
    except OSError:
        return None


class CafeMiceWindow:
    def __init__(self, patcher):
        import tkinter as tk
        from PIL import ImageTk

        self.tk = tk
        self.p = patcher
        self.lines = queue.Queue()
        self.log_lines = []
        sys.stdout = sys.stderr = _Lines(self.lines)

        root = self.root = tk.Tk()
        root.title("CafeMice")
        root.resizable(False, False)
        icon = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "cafemice.ico"
        if icon.is_file():
            try:
                root.iconbitmap(str(icon))
            except tk.TclError:
                pass

        c = self.canvas = tk.Canvas(root, width=W, height=H, highlightthickness=0, bd=0)
        c.pack()
        self._bg = ImageTk.PhotoImage(_background(_game_icon(patcher.folder)))
        c.create_image(0, 0, image=self._bg, anchor="nw")

        self.mod_dot = c.create_oval(52, 170, 66, 184, outline="")
        self.mod_text = c.create_text(76, 177, anchor="w", font=("Segoe UI", 13, "bold"))
        self.run_dot = c.create_oval(52, 206, 66, 220, outline="")
        self.run_text = c.create_text(76, 213, anchor="w", font=("Segoe UI", 12, "bold"))

        self.buttons = {}
        self._make_button("play", "Modu kur ve oyna", "green", 270, self.on_play)
        self._make_button("remove", "Modu kaldır", "wood", 336, self.on_remove)

        self.message = c.create_text(W // 2, 432, width=W - 80, font=("Segoe UI", 10, "bold"), fill=TEXT_INK,
                                     justify="center")
        self.log = c.create_text(44, 462, anchor="nw", width=W - 88, font=("Consolas", 8), fill=DIM)

        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.refresh()
        root.after(300, self.tick)

    def _make_button(self, name, text, kind, y, command):
        from PIL import ImageTk
        images = {state: ImageTk.PhotoImage(_button(text, kind, state, arrow=name == "play"))
                  for state in ("normal", "hover", "pressed", "disabled")}
        item = self.canvas.create_image(26, y, image=images["normal"], anchor="nw")
        b = self.buttons[name] = {"item": item, "images": images, "enabled": True, "command": command}
        c = self.canvas

        def show(state):
            c.itemconfigure(item, image=images[state if b["enabled"] else "disabled"])

        c.tag_bind(item, "<Enter>", lambda e: (show("hover"), c.configure(cursor="hand2" if b["enabled"] else "")))
        c.tag_bind(item, "<Leave>", lambda e: (show("normal"), c.configure(cursor="")))
        c.tag_bind(item, "<ButtonPress-1>", lambda e: show("pressed"))

        def release(e):
            show("hover")
            if b["enabled"]:
                command()

        c.tag_bind(item, "<ButtonRelease-1>", release)

    def _enable(self, name, on):
        b = self.buttons[name]
        if b["enabled"] != on:
            b["enabled"] = on
            self.canvas.itemconfigure(b["item"], image=b["images"]["normal" if on else "disabled"])

    def say(self, text, color=TEXT_INK):
        self.canvas.itemconfigure(self.message, text=text, fill=color)

    def refresh(self):
        c = self.canvas
        status = self.p.status()
        if status == "no_game":
            c.itemconfigure(self.mod_dot, fill=BAD)
            c.itemconfigure(self.mod_text, text="Transformice bulunamadı (Steam'den kur)", fill=BAD)
        elif status == "installed":
            c.itemconfigure(self.mod_dot, fill=GOOD)
            c.itemconfigure(self.mod_text, text="Mod: kurulu", fill=GOOD)
        else:
            c.itemconfigure(self.mod_dot, fill=DIM)
            c.itemconfigure(self.mod_text, text="Mod: kurulu değil", fill=DIM)
        if self.p.running:
            c.itemconfigure(self.run_dot, fill=GOOD)
            c.itemconfigure(self.run_text, text="CafeMice: çalışıyor (pencereyi kapatma)", fill=GOOD)
        else:
            c.itemconfigure(self.run_dot, fill=DIM)
            c.itemconfigure(self.run_text, text="CafeMice: kapalı", fill=DIM)
        self._enable("play", status != "no_game")
        self._enable("remove", status == "installed")

    def on_play(self):
        if self.p.play() == "no_game":
            self.say("Önce Transformice'i Steam'den kur.", BAD)
        else:
            self.say("Oyun açılıyor... Oynarken bu pencere açık kalsın, alta küçültebilirsin.")
        self.refresh()

    def on_remove(self):
        if self.p.remove() == "removed":
            self.say("Mod kaldırıldı. Oyun artık Steam'den normal açılır.")
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
        changed = False
        while not self.lines.empty():
            line = self.lines.get_nowait()
            self.log_lines.append(line[:70])
            changed = True
        if changed:
            self.log_lines = self.log_lines[-5:]
            self.canvas.itemconfigure(self.log, text="\n".join(self.log_lines))
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
    sys.exit(main())
