"""Local caseus proxy for the Café: blocking, favourites, notes, the archive and more.

Run from the project root, then start the game (Steam's Transformice.swf
replaced by the patched TFMProxyLoader with the "Sil" menu item):

    python -m cafemice

The loader adds "Sil", "Favori" and "PP indir" to the menu of a Café post and
talks to CONTROL_PORT, one command per line (arguments tab-separated):

    BLOCK name / UNBLOCK name   hide / show a player's posts, topics, notifications
    FAV author<TAB>text         keep a message (cafe_favorites.json in the data folder)
    UNFAV id                    forget it
    PP name                     save the player's avatar to PP_DIR
    WATCH name / UNWATCH name   ring (or stop) when the player posts in the Café
    SHOT base64-png             save a Café screenshot to SHOT_DIR and upload it
    NOTE name<TAB>text          a private note shown next to the name (empty: remove)
    SEARCH words                search the archive of every post seen ("@name" = author)
    PREVIEW url                 a thumbnail of an image link (catbox, imgur, prnt.sc)
    GOTO topic                  open that Café topic (the game shows it as if clicked)
    LIST                        ask for the state
    LOG text                    a line for this console

Replies: "STATE <json>" ({"blocked", "favs", "watched", "notes", "me"}) after
every change and on LIST, "TOAST <text>" to show the player a short message,
"NOTIFY name" when a watched player posts, "MENTION name<TAB>topic" when a new
post names or quotes the player, "LINK url" (copied to the clipboard) for an
uploaded screenshot, "RESULTS <json>" for a search and "PREVIEW url base64" (or
"PREVIEW url -") for a link thumbnail.

The topic list does not say who opened a topic, so when it shows topics with
an unknown owner the proxy opens them in the background (one at a time) and
keeps the answers from the game; a topic of a blocked player then leaves the
list. Owners are remembered, so each topic is asked about once.
"""

import asyncio
import base64
import html
import io
import json
import re
import time
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import urljoin, urlparse

import caseus
from caseus.proxies import Proxy

from .cafe_archive import Archive, mentions
from .cafe_block import (
    Blocklist,
    Favorites,
    Notes,
    Watchlist,
    _key,
    name_matches,
    avatar_url,
    parse_posts,
    parse_topics,
)
from .cafe_gif import GifAvatars

CONTROL_HOST = "127.0.0.1"
CONTROL_PORT = 11810


def pictures_dir():
    """Windows' own Pictures folder (OneDrive moves it), else ~/Pictures."""
    try:
        import ctypes

        # FOLDERID_Pictures {33E28130-4E1E-4676-835A-98395C3BC3BB}, as a GUID struct
        guid = (ctypes.c_byte * 16).from_buffer_copy(
            bytes.fromhex("3081e2331e4e7646835a98395c3bc3bb"))
        out = ctypes.c_wchar_p()
        if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(out)) == 0:
            path = Path(out.value)
            ctypes.windll.ole32.CoTaskMemFree(out)
            return path
    except (AttributeError, OSError, ValueError):
        pass
    return Path.home() / "Pictures"


PP_DIR = pictures_dir() / "Transformice PP"
SHOT_DIR = pictures_dir() / "Transformice SS"
UPLOAD_URL = "https://catbox.moe/user/api.php"  # anonymous image host
PROBE_DELAY = 0.4  # s between background topic requests
CONTROL_LIMIT = 16 * 1024 * 1024  # a screenshot line is a few hundred KB

# Image links worth a preview: only these sites are ever fetched (the links
# come from other players' messages).
PREVIEW_HOSTS = ("catbox.moe", "imgur.com", "prnt.sc", "prntscr.com")
PREVIEW_SIZE = (320, 220)
PREVIEW_MAX_BYTES = 8 * 1024 * 1024
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp")


def _log(text):
    print(time.strftime("%H:%M:%S"), text, flush=True)


def _fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.read()


def preview_allowed(url):
    try:
        parts = urlparse(url)
    except ValueError:
        return False
    host = (parts.hostname or "").lower()
    return parts.scheme in ("http", "https") and any(host == h or host.endswith("." + h) for h in PREVIEW_HOSTS)


def _og_image(page, base):
    """The page's og:image (prnt.sc and imgur pages), or None."""
    m = (re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', page)
         or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image', page))
    return urljoin(base, html.unescape(m.group(1))) if m else None


def make_preview(url, fetch):
    """A small PNG of the image behind an allowed link."""
    from PIL import Image

    if not preview_allowed(url):
        raise ValueError("site not allowed")
    data = fetch(url)
    if not urlparse(url).path.lower().endswith(IMAGE_EXT):
        image_url = _og_image(data[:400000].decode("utf-8", "replace"), url)
        if not image_url or not preview_allowed(image_url):
            raise ValueError("no image on the page")
        data = fetch(image_url)
    if len(data) > PREVIEW_MAX_BYTES:
        raise ValueError("image too big")
    with Image.open(io.BytesIO(data)) as im:
        im = im.convert("RGBA")
        im.thumbnail(PREVIEW_SIZE)
        out = io.BytesIO()
        im.save(out, "PNG", optimize=True)
    return out.getvalue()


def _upload(path):
    """Upload an image anonymously; its public address."""
    path = Path(path)
    boundary = uuid.uuid4().hex
    head = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"reqtype\"\r\n\r\nfileupload\r\n"
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"fileToUpload\"; filename=\"{path.name}\"\r\n"
            "Content-Type: image/png\r\n\r\n")
    body = head.encode() + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    request = urllib.request.Request(UPLOAD_URL, data=body, headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        url = response.read().decode("utf-8", "replace").strip()
    if not url.startswith("https://"):
        raise ValueError(url[:200])
    return url

class CafeProxy(Proxy):
    def __init__(self, *args, blocklist=None, favorites=None, gifs=None, watchlist=None, pp_dir=PP_DIR,
                 shot_dir=SHOT_DIR, fetch=None, upload=None, probe_delay=PROBE_DELAY, archive=None,
                 notes=None, me=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.archive = archive if archive is not None else Archive()
        self.notes = notes if notes is not None else Notes()
        self.me = me  # this player's name, from the login
        self._previews = {}  # url -> reply line
        self._wanted = set()  # topics to ask about even with a known owner
        self.blocklist = blocklist or Blocklist()
        self.favorites = favorites or Favorites()
        self.watchlist = watchlist or Watchlist()
        self.shot_dir = Path(shot_dir)
        self._upload = upload or _upload
        self.probe_delay = probe_delay
        self._last_list = None  # the last topic list from the server
        self._probe_queue = []  # topic ids to ask about
        self._probing = set()  # asked, answer not seen yet
        self._prober = None
        self.gifs = gifs if gifs is not None else GifAvatars()
        self.pp_dir = Path(pp_dir)
        self._fetch = fetch or _fetch
        self._loaders = set()  # control writers
        self._cafe_server = None  # the server connection that serves the Café
        self._open_topic = None
        self.register_packet_listener(self._on_posts, caseus.clientbound.CafeTopicPostsPacket)
        self.register_packet_listener(self._on_list, caseus.clientbound.CafeListPacket)
        self.register_packet_listener(self._on_notification, caseus.clientbound.CafeNewPostNotificationPacket)
        self.register_packet_listener(self._on_open_topic, caseus.serverbound.CafeOpenTopicPacket)
        self.register_packet_listener(self._on_login, caseus.clientbound.LoginSuccessPacket)

    # --- game traffic ---------------------------------------------------

    async def _on_login(self, source, packet):
        if packet.username and packet.username != self.me:
            self.me = packet.username
            _log(f"logged in as {self.me}")
            await self._broadcast([self.state_line()])

    async def _archive(self, parsed):
        """Keep the posts; ring for new ones that name or quote this player."""
        if parsed is None:
            return
        topic_id, posts = parsed
        known = self.archive.has_topic(topic_id)
        new = self.archive.add_posts(topic_id, posts)
        if not known or not self.me:
            return  # the first look at a topic is history, not news
        for post in new:
            if post["author"].lower() != self.me.lower() and mentions(post["text"], self.me) \
                    and not self.blocklist.is_blocked(post["author"]):
                _log(f"{post['author']} wrote to you in topic {topic_id}")
                await self._broadcast([f"MENTION {post['author']}\t{self.archive.title(topic_id)}"])

    async def _on_open_topic(self, source, packet):
        self._open_topic = packet.topic_id
        # The player asked for it: the answer goes to the game.
        self._probing.discard(packet.topic_id)

    async def _on_posts(self, source, packet):
        self._cafe_server = source
        parsed = parse_posts(packet.data)
        if parsed is not None and parsed[0] in self._probing:
            # Our background question: learn the owner, keep it from the game.
            topic_id = parsed[0]
            self._probing.discard(topic_id)
            self.blocklist.filter_posts(packet.data)
            await self._archive(parsed)
            if self.blocklist.topic_blocked(topic_id):
                _log(f"topic {topic_id} was opened by {self.blocklist.owners[topic_id]}: hiding it")
                await self._resend_list(source)
            return self.DO_NOTHING
        new = self.blocklist.filter_posts(packet.data)
        await self._archive(parsed)
        await self._learn_gif_avatars()
        data = bytes(new) if new is not None else bytes(packet.data)
        if new is None:
            return None
        if new is not None:
            _log(f"topic posts: hid {len(packet.data) - len(new)} bytes of blocked posts")
        await source.destination.write_packet(caseus.clientbound.CafeTopicPostsPacket, data=bytearray(data))
        return self.DO_NOTHING

    async def _learn_gif_avatars(self):
        """A GIF player's avatar id showed up in the posts: send their GIF."""
        for key, entry in list(self.gifs.entries.items()):
            avatar = self.blocklist.avatars.get(key)
            if avatar and self.gifs.learn(entry["name"], avatar):
                _log(f"avatar id of {entry['name']} is {avatar}: sending the GIF")
                line = self.gifs.line_for(entry["name"])
                if line:
                    await self._broadcast([line])

    async def _on_list(self, source, packet):
        self._cafe_server = source
        self._last_list = bytes(packet.data)
        self.archive.add_topics(parse_topics(packet.data) or [])
        if self.blocklist.names:
            self._queue_probes(source, self.blocklist.unknown_topics(packet.data))
        new = self.blocklist.filter_topics(packet.data, self._last_poster)
        data = bytes(new) if new is not None else bytes(packet.data)
        if new is None:
            return None
        if new is not None:
            _log("topic list: hid topics of blocked players")
        await source.destination.write_packet(caseus.clientbound.CafeListPacket, data=bytearray(data))
        return self.DO_NOTHING

    async def _on_notification(self, source, packet):
        if self.blocklist.drop_notification(packet.topic_id, packet.username):
            _log(f"dropped Café notification from {packet.username}")
            return self.DO_NOTHING
        if self.watchlist.watched(packet.username):
            _log(f"{packet.username} posted in the Café")
            await self._broadcast([f"NOTIFY {packet.username}"])
        if self.me and packet.username.lower() != self.me.lower() and packet.topic_id != self._open_topic:
            # Read the new post in the background: does it name this player?
            self._wanted.add(packet.topic_id)
            self._queue_probes(source, [packet.topic_id])
        return None

    # --- who opened which topic -----------------------------------------

    def _queue_probes(self, server, topic_ids):
        new = [t for t in topic_ids if t not in self._probe_queue and t not in self._probing]
        if not new:
            return
        self._probe_queue.extend(new)
        if self._prober is None or self._prober.done():
            self._prober = asyncio.ensure_future(self._probe(server))

    async def _probe(self, server):
        if len(self._probe_queue) > 1:
            _log(f"asking who opened {len(self._probe_queue)} Café topics")
        while self._probe_queue:
            topic_id = self._probe_queue.pop(0)
            if server.is_closing():
                self._probe_queue.clear()
                return
            wanted = topic_id in self._wanted
            self._wanted.discard(topic_id)
            if (topic_id in self.blocklist.owners and not wanted) or topic_id == self._open_topic:
                continue
            self._probing.add(topic_id)
            await server.write_packet(caseus.serverbound.CafeOpenTopicPacket, topic_id=topic_id)
            await asyncio.sleep(self.probe_delay)
        # An answer that never came (a deleted topic) must not hide a later open.
        await asyncio.sleep(max(self.probe_delay, 2))
        self._probing.clear()

    def _last_poster(self, topic_id):
        """The topic's last poster who is not blocked, from the archive."""
        author = self.archive.last_author(topic_id, skip=self.blocklist.is_blocked_name)
        # The list shows names without their #tag.
        return author.split("#", 1)[0] if author else None

    async def _resend_list(self, server):
        if self._last_list is None:
            return
        new = self.blocklist.filter_topics(self._last_list, self._last_poster)
        if new is not None:
            await server.destination.write_packet(caseus.clientbound.CafeListPacket, data=bytearray(new))

    async def _refresh_cafe(self):
        """Ask the server again so the open Café is redrawn without the blocked player."""
        server = self._cafe_server
        if server is None or server.is_closing():
            return
        await server.write_packet(caseus.serverbound.CafeRefreshPacket)
        if self._open_topic is not None:
            await server.write_packet(caseus.serverbound.CafeOpenTopicPacket, topic_id=self._open_topic)

    # --- control socket (the patched loader) ----------------------------

    def _place_favorites(self):
        """Favourites learn their topic, post and avatar from the archive."""
        changed = False
        for fav in self.favorites.items:
            if fav.get("post"):
                continue
            found = self.archive.find(fav["author"], fav["text"])
            if found:
                fav.update(found)
                changed = True
        if changed:
            self.favorites.save()

    def state_line(self):
        self._place_favorites()
        state = {"blocked": sorted(self.blocklist.names.values(), key=str.lower), "favs": self.favorites.items,
                 "watched": sorted(self.watchlist.names.values(), key=str.lower),
                 "notes": self.notes.items, "me": self.me or ""}
        return "STATE " + json.dumps(state, ensure_ascii=False, separators=(",", ":"))

    def _server_connection(self):
        server = self._cafe_server
        if server is not None and not server.is_closing():
            return server
        for client in reversed(getattr(self, "main_clients", [])):
            destination = getattr(client, "destination", None)
            if destination is not None and not destination.is_closing():
                return destination
        return None

    async def handle(self, line):
        """Run one loader command; the reply lines to send back."""
        command, _, arg = line.strip().partition(" ")
        if command == "LOG":
            _log(f"[loader] {arg}")
            return []
        if command == "LIST":
            return [self.state_line()] + self.gifs.lines()
        if command == "BLOCK":
            added = self.blocklist.block(arg)
            _log(f"blocked {arg}" if added else f"{arg} was already blocked")
            await self._refresh_cafe()
            return [self.state_line()]
        if command == "UNBLOCK":
            removed = self.blocklist.unblock(arg)
            _log(f"unblocked {arg}" if removed else f"{arg} was not blocked")
            await self._refresh_cafe()
            return [self.state_line(), f"TOAST {arg} artık görünüyor" if removed else f"TOAST {arg} engelli değildi"]
        if command == "FAV":
            author, _, text = arg.partition("\t")
            added = self.favorites.add(author, text)
            _log(f"favourite from {author}" if added else f"favourite from {author} already kept")
            return [self.state_line(), "TOAST Favorilere eklendi" if added else "TOAST Zaten favorilerde"]
        if command == "UNFAV":
            try:
                self.favorites.remove(int(arg))
            except ValueError:
                pass
            return [self.state_line()]
        if command == "PP":
            return [await self.save_avatar(arg)]
        if command == "WATCH":
            on = self.watchlist.toggle(arg)
            _log(f"watching {arg}" if on else f"stopped watching {arg}")
            return [self.state_line(), f"TOAST {arg}: bildirim açık" if on else f"TOAST {arg}: bildirim kapalı"]
        if command == "UNWATCH":
            self.watchlist.remove(arg)
            return [self.state_line(), f"TOAST {arg}: bildirim kapalı"]
        if command == "SHOT":
            return await self.save_shot(arg)
        if command == "NOTE":
            name, _, text = arg.partition("\t")
            self.notes.set(name, text)
            return [self.state_line(), f"TOAST {name}: not kaydedildi" if text.strip() else f"TOAST {name}: not silindi"]
        if command == "SEARCH":
            results = self.archive.search(arg)
            return ["RESULTS " + json.dumps({"query": arg, "results": results}, ensure_ascii=False, separators=(",", ":"))]
        if command == "PREVIEW":
            return [await self.preview(arg.strip())]
        if command == "GOTO":
            return await self.goto(arg)
        return []

    async def goto(self, arg):
        try:
            topic_id = int(arg.split()[0])
        except (ValueError, IndexError):
            return []
        server = self._cafe_server
        if server is None or server.is_closing():
            return ["TOAST Önce Café'yi aç"]
        self._open_topic = topic_id
        self._probing.discard(topic_id)
        await server.write_packet(caseus.serverbound.CafeOpenTopicPacket, topic_id=topic_id)
        return []

    async def preview(self, url):
        if url not in self._previews:
            try:
                png = await asyncio.to_thread(make_preview, url, self._fetch)
                line = f"PREVIEW {url} " + base64.b64encode(png).decode("ascii")
            except Exception as exc:  # network errors, not an image, a site not allowed
                _log(f"no preview for {url}: {exc}")
                line = f"PREVIEW {url} -"
            if len(self._previews) > 100:
                self._previews.clear()
            self._previews[url] = line
        return self._previews[url]

    async def save_shot(self, data):
        try:
            png = base64.b64decode(data.strip())
        except ValueError:
            png = b""
        if not png.startswith(b"\x89PNG"):
            return ["TOAST Ekran görüntüsü okunamadı"]
        self.shot_dir.mkdir(parents=True, exist_ok=True)
        path = self.shot_dir / time.strftime("cafe_%Y-%m-%d_%H-%M-%S.png")
        path.write_bytes(png)
        _log(f"screenshot saved to {path}")
        try:
            url = await asyncio.to_thread(self._upload, path)
        except Exception as exc:  # network errors, HTTP errors, a refused upload
            _log(f"screenshot upload failed: {exc}")
            return [f"TOAST Yüklenemedi, kaydedildi: {path.name}"]
        _log(f"screenshot uploaded: {url}")
        return [f"LINK {url}", f"TOAST Link kopyalandı: {url}"]

    async def save_avatar(self, name):
        avatar = self.blocklist.avatars.get(name.strip().lower())
        if not avatar:
            return f"TOAST {name}: avatarı yok ya da henüz görülmedi"
        url = avatar_url(avatar)
        try:
            data = await asyncio.to_thread(self._fetch, url)
        except Exception as exc:  # network errors, HTTP errors
            _log(f"avatar of {name}: {exc}")
            return f"TOAST {name}: indirilemedi"
        self.pp_dir.mkdir(parents=True, exist_ok=True)
        path = self.pp_dir / (re.sub(r"[^\w#.-]", "_", name.strip()).replace("#", "_") + ".jpg")
        path.write_bytes(data)
        _log(f"avatar of {name} saved to {path}")
        return f"TOAST PP kaydedildi: {path.name}"

    async def _broadcast(self, lines):
        for writer in list(self._loaders):
            try:
                for reply in lines:
                    writer.write((reply + "\n").encode("utf-8"))
                await writer.drain()
            except (ConnectionError, RuntimeError):
                self._loaders.discard(writer)

    async def _on_control(self, reader, writer):
        self._loaders.add(writer)
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break
                replies = await self.handle(line.decode("utf-8", "replace"))
                if replies:
                    # Every loader sees the same state (the game may reconnect).
                    await self._broadcast(replies)
        except (ConnectionError, asyncio.IncompleteReadError, ValueError):
            pass
        finally:
            self._loaders.discard(writer)
            writer.close()

    async def on_start(self):
        control = await asyncio.start_server(self._on_control, CONTROL_HOST, CONTROL_PORT, limit=CONTROL_LIMIT)
        _log(f"Café block proxy: game on localhost:11801, loader control on {CONTROL_HOST}:{CONTROL_PORT}")
        _log(f"blocked: {', '.join(self.blocklist.names.values()) or '-'}; favourites: {len(self.favorites.items)}")
        async with control:
            await asyncio.gather(super().on_start(), control.serve_forever())


if __name__ == "__main__":
    CafeProxy().run()
