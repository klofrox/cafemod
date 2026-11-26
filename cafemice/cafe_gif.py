"""GIF avatars seen only in this game client.

Flash shows only the first frame of a GIF, so the proxy splits each GIF into
PNG frames (cropped to a centred square) and the patched loader plays them
by redrawing the avatar image the game already shows for that player.

cafe_gifs.json (in the data folder) maps a player to a GIF (paths relative to the
data folder); the player's avatar id is learned from the Café posts
and kept in the same file so it works before the Café is opened again:

    {"Ornek#1234": {"gif": "gifs/ornek.gif", "avatar": 1234567}}
"""

import base64
import io
import json
from pathlib import Path

from .paths import DATA_DIR

from PIL import Image, ImageSequence

HERE = DATA_DIR
GIFS_PATH = HERE / "cafe_gifs.json"
FRAME_SIZE = 64  # px, square; the game keeps avatars as 50x50 images
MIN_DELAY_MS = 20


def _key(name):
    return str(name or "").strip().lower()


def gif_frames(path, size=FRAME_SIZE):
    """([png bytes], [delay ms]) of a GIF, each frame a centred square."""
    frames, delays = [], []
    with Image.open(path) as im:
        for frame in ImageSequence.Iterator(im):
            rgba = frame.convert("RGBA")
            w, h = rgba.size
            side = min(w, h)
            left, top = (w - side) // 2, (h - side) // 2
            square = rgba.crop((left, top, left + side, top + side)).resize((size, size), Image.LANCZOS)
            out = io.BytesIO()
            square.save(out, "PNG", optimize=True)
            frames.append(out.getvalue())
            delays.append(max(MIN_DELAY_MS, int(frame.info.get("duration", im.info.get("duration", 100)) or 100)))
    return frames, delays


class GifAvatars:
    def __init__(self, path=GIFS_PATH):
        self.path = Path(path)
        self.entries = {}  # key -> {"name", "gif", "avatar"}
        self._lines = {}  # avatar id -> "GIF ..." line, built once
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raw = {}
        for name, entry in raw.items():
            if isinstance(entry, str):
                entry = {"gif": entry}
            self.entries[_key(name)] = {"name": name, "gif": entry.get("gif"), "avatar": entry.get("avatar")}

    def save(self):
        data = {e["name"]: {k: v for k, v in (("gif", e["gif"]), ("avatar", e["avatar"])) if v} for e in self.entries.values()}
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self.path)

    def learn(self, name, avatar_id):
        """A post showed this player's avatar id; True when it is new for a GIF player."""
        entry = self.entries.get(_key(name))
        if entry is None or not avatar_id or entry["avatar"] == int(avatar_id):
            return False
        entry["avatar"] = int(avatar_id)
        self.save()
        return True

    def line(self, entry):
        """'GIF <avatar id> <delays,...> <base64 png,...>' for the loader, or None."""
        if not entry.get("avatar") or not entry.get("gif"):
            return None
        avatar = int(entry["avatar"])
        if avatar not in self._lines:
            path = Path(entry["gif"])
            if not path.is_absolute():
                path = self.path.parent / path
            frames, delays = gif_frames(path)
            self._lines[avatar] = "GIF {} {} {}".format(
                avatar, ",".join(map(str, delays)), ",".join(base64.b64encode(f).decode("ascii") for f in frames))
        return self._lines[avatar]

    def lines(self):
        out = []
        for entry in self.entries.values():
            try:
                line = self.line(entry)
            except (OSError, ValueError) as exc:
                print(f"GIF of {entry['name']}: {exc}", flush=True)
                continue
            if line:
                out.append(line)
        return out

    def line_for(self, name):
        entry = self.entries.get(_key(name))
        return self.line(entry) if entry else None
