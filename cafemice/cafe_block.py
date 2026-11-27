"""Hide blocked players in the Café, on this client only.

The game client connects through the local caseus proxy (see
cafe_block_proxy.py). Packets from the server are rewritten before the game
sees them:

* topic posts (30, 41): posts written by a blocked player, and posts quoting
  one ("> @Name" lines, what the game's "Alıntıla" writes), are removed;
* topic list (30, 40): topics opened by a blocked player are removed (the
  list does not say who opened a topic: the proxy learns it from the posts);
* new post notification (30, 44): dropped when it is about a blocked player.

Layouts, read from the game's own packet readers (payload after the 2-byte id):

  posts: bool ok; if ok: int topic_id, bool, bool, then posts until the end:
         int post_id, int avatar_id, int time, UTF author, UTF text, bool, short, UTF, byte marker
  list:  bool, bool, then topics until the end:
         int topic_id, UTF title, int, int, UTF name, int

UTF is a big-endian u16 byte length followed by UTF-8.
"""

import json
import re
import struct
import time
from pathlib import Path

from .paths import DATA_DIR

BLOCKLIST_PATH = DATA_DIR / "cafe_blocklist.json"
FAVORITES_PATH = DATA_DIR / "cafe_favorites.json"
WATCH_PATH = DATA_DIR / "cafe_watch.json"

# The game's "Alıntıla" starts the reply with "> @Name" (the name without its #tag).
QUOTE_RE = re.compile(r"^>\s*@([^\s#<>]+)(#\d{4})?", re.M)

# The game shows a player's avatar from this address (only the 50x50 copy exists).
AVATAR_URL = "http://avatars.atelier801.com/{bucket}/{id}_50.jpg"


# The post whose marker byte has this value makes the game set the topic's
# owner name from it (the topic's opening post).
OWNER_MARKER = 1


def _key(name):
    return str(name or "").strip().lower()


def _base(name):
    return _key(name).split("#", 1)[0]


def name_matches(typed, name):
    """Is ``name`` the player that was typed? "Name" (no #tag) matches any tag."""
    if not _key(typed) or not _key(name):
        return False
    if "#" in str(typed):
        return _key(name) == _key(typed)
    return _base(name) == _key(typed)


def _utf(data, pos):
    (length,) = struct.unpack_from(">H", data, pos)
    end = pos + 2 + length
    if end > len(data):
        raise struct.error("string past the end")
    return bytes(data[pos + 2:end]).decode("utf-8", "replace"), end


def parse_posts(data):
    """(topic_id, posts) of a posts payload, or None if it cannot be read.

    Each post: {"start", "end", "post_id", "avatar", "time", "author", "text",
    "marker", "raw"}; start/end are byte offsets of the post inside ``data``, raw
    its bytes."""
    data = bytes(data)
    try:
        if not data or not data[0]:
            return None
        (topic_id,) = struct.unpack_from(">i", data, 1)
        pos = 1 + 4 + 1 + 1
        if pos > len(data):
            return None
        posts = []
        while pos < len(data):
            start = pos
            post_id, avatar, posted = struct.unpack_from(">iii", data, pos)
            pos += 12
            author, pos = _utf(data, pos)
            text, pos = _utf(data, pos)
            (score,) = struct.unpack_from(">h", data, pos + 1)
            pos += 1 + 2
            _extra, pos = _utf(data, pos)
            if pos >= len(data):
                return None
            marker = data[pos]
            pos += 1
            posts.append({"start": start, "end": pos, "post_id": post_id, "avatar": avatar, "time": posted,
                          "author": author, "text": text, "marker": marker, "score": score,
                          "raw": data[start:pos]})
    except struct.error:
        return None
    return topic_id, posts


POSTS_HEADER = 1 + 4 + 1 + 1  # ok, topic id, two flags


def pack_post(post_id, avatar, posted, author, text, marker=0):
    """One post in the layout parse_posts reads (no likes, no extra text)."""
    return (struct.pack(">iii", int(post_id), int(avatar or 0), int(posted or 0)) + _pack_utf(author)
            + _pack_utf(text) + b"\x00" + struct.pack(">h", 0) + _pack_utf("") + bytes([int(marker) & 0xFF]))


# The topic id of the "show all messages of <name>" view the proxy answers
# from its archive. The server never hands out topic ids this high.
ALL_MESSAGES_TOPIC_ID = 2_000_000_000


def retext_post(raw, change, marker=None):
    """One post's bytes with its text replaced by ``change(text)`` (and its
    marker byte by ``marker`` when given); score and label are kept."""
    raw = bytes(raw)
    _author, pos = _utf(raw, 12)
    text, end = _utf(raw, pos)
    tail = raw[end:]
    if marker is not None:
        tail = tail[:-1] + bytes([int(marker) & 0xFF])
    return raw[:pos] + _pack_utf(change(text)) + tail


def all_messages_payload(posts, topic_id=ALL_MESSAGES_TOPIC_ID, title=None):
    """A posts payload of archived ``posts`` (Archive.by_author rows): no
    moderation buttons, no reply box. Archived bytes are kept as they were,
    but their marker is cleared so no post renames the view's owner.

    ``title(topic_id)`` names each post's topic: it goes on the post's first line."""
    out = bytearray(b"\x01" + struct.pack(">i", int(topic_id)) + b"\x00\x00")
    for p in posts:
        name = (title(p["topic_id"]) if title and p.get("topic_id") is not None else "") or ""

        def change(text, name=name):
            return f"[{name}]\r{text}" if name else text

        raw = p.get("raw")
        if raw:
            out += retext_post(raw, change, marker=0)
        else:
            out += pack_post(p["post_id"], p.get("avatar"), p.get("time"), p["author"], change(p["text"]))
    return bytes(out)


DELETED_MARK = "(silindi) "
# A deletion takes a post or a few; a longer run of missing posts is the
# server shortening a long topic, not a deletion.
DELETED_RUN = 3
# At most this many deleted posts come back per topic (each one is drawn).
DELETED_LIMIT = 50


def deleted_rows(archived, sent_ids, run=DELETED_RUN, limit=DELETED_LIMIT):
    """The ``archived`` rows (a topic's posts from its first one sent on, in
    post id order) the server left out by deleting them: runs of at most
    ``run`` missing posts; the newest ``limit`` of them."""
    out, gap = [], []
    for row in archived:
        if row["post_id"] in sent_ids:
            if len(gap) <= run:
                out += gap
            gap = []
        else:
            gap.append(row)
    if len(gap) <= run:
        out += gap
    return out[-limit:] if limit else []


def with_posts_merged(data, extra):
    """The posts payload with ``extra`` post bytes put among its own posts in
    post id order."""
    data = bytes(data)
    parsed = parse_posts(data)
    if parsed is None:
        return data
    raws = [p["raw"] for p in parsed[1]] + [bytes(r) for r in extra]
    raws.sort(key=lambda r: struct.unpack_from(">i", r, 0)[0])
    return data[:POSTS_HEADER] + b"".join(raws)


def with_older_posts(data, older):
    """The posts payload with ``older`` (post bytes, oldest first) before its own posts."""
    data = bytes(data)
    return data[:POSTS_HEADER] + b"".join(older) + data[POSTS_HEADER:]


def parse_topics(data):
    """Topics of a list payload: [{"start", "end", "id", "title", "name", "name_at"}], or None.

    ``name`` is the topic's last poster; ``name_at`` the (start, end) of its string."""
    data = bytes(data)
    try:
        if len(data) < 2:
            return None
        pos = 2
        topics = []
        while pos < len(data):
            start = pos
            (topic_id,) = struct.unpack_from(">i", data, pos)
            title, pos = _utf(data, pos + 4)
            pos += 8
            name_start = pos
            name, pos = _utf(data, pos)
            name_end = pos
            struct.unpack_from(">i", data, pos)
            pos += 4
            topics.append({"start": start, "end": pos, "id": topic_id, "title": title, "name": name,
                           "name_at": (name_start, name_end)})
    except struct.error:
        return None
    return topics


def with_mod_flag(data):
    """List payload with its second bool (the game's Café moderator flag) set;
    None when it already is.

    With the flag on, the game's like/dislike moves a post's score by 15000
    on screen instead of 1. Only this client's display changes."""
    data = bytes(data)
    if len(data) < 2 or data[1]:
        return None
    return data[:1] + b"\x01" + data[2:]


def avatar_url(avatar_id):
    avatar_id = int(avatar_id)
    return AVATAR_URL.format(bucket=avatar_id % 10000, id=avatar_id)


def topic_owner(posts):
    """Who opened the topic: the author of its first post.

    The server sends a topic's posts whole (the list's post count matches),
    so the oldest post (lowest id) is the opening one. (The marker byte is a
    post's moderation state, not "opening post": owners read from it were
    almost never found.)"""
    if not posts:
        return None
    return min(posts, key=lambda p: p["post_id"])["author"]


def _without(data, spans):
    out = bytearray()
    pos = 0
    for start, end in spans:
        out += data[pos:start]
        pos = end
    out += data[pos:]
    return bytes(out)


def _pack_utf(text):
    raw = str(text).encode("utf-8")
    return struct.pack(">H", len(raw)) + raw


class Blocklist:
    """Blocked names and the known owners of Café topics, kept in a JSON file."""

    def __init__(self, path=BLOCKLIST_PATH):
        self.path = Path(path)
        self.names = {}  # key -> name as written
        self.owners = {}  # topic id -> owner name
        self.avatars = {}  # key -> avatar id, from the posts seen (not saved)
        self.load()

    def load(self):
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        self.names = {_key(n): n for n in raw.get("blocked", []) if _key(n)}
        self.owners = {int(k): v for k, v in (raw.get("topic_owners") or {}).items()}

    def save(self):
        data = {"blocked": sorted(self.names.values(), key=str.lower),
                "topic_owners": {str(k): v for k, v in sorted(self.owners.items())}}
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self.path)

    def block(self, name):
        if not _key(name) or _key(name) in self.names:
            return False
        self.names[_key(name)] = str(name).strip()
        self.save()
        return True

    def unblock(self, name):
        if self.names.pop(_key(name), None) is None:
            return False
        self.save()
        return True

    def is_blocked(self, name):
        return _key(name) in self.names

    def quotes_blocked(self, text):
        """True when the text quotes a blocked player."""
        bases = {_base(n) for n in self.names}
        # The game ends lines with \r.
        text = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
        for m in QUOTE_RE.finditer(text):
            name, tag = m.group(1).lower(), m.group(2)
            if (name + tag if tag else name) in self.names or (not tag and name in bases):
                return True
        return False

    def topic_blocked(self, topic_id):
        owner = self.owners.get(int(topic_id))
        return owner is not None and self.is_blocked(owner)

    def learn_owner(self, topic_id, owner):
        if owner and self.owners.get(int(topic_id)) != owner:
            self.owners[int(topic_id)] = owner
            self.save()

    # --- packet payloads --------------------------------------------------

    def filter_posts(self, data):
        """Posts payload without blocked authors; None when nothing changes."""
        data = bytes(data)
        parsed = parse_posts(data)
        if parsed is None:
            return None
        topic_id, posts = parsed
        self.learn_owner(topic_id, topic_owner(posts))
        for p in posts:
            if p["avatar"] > 0:
                self.avatars[_key(p["author"])] = p["avatar"]
        spans = [(p["start"], p["end"]) for p in posts
                 if self.is_blocked(p["author"]) or self.quotes_blocked(p["text"])]
        return _without(data, spans) if spans else None

    def unknown_topics(self, data):
        """Ids of the listed topics whose owner is not known yet."""
        topics = parse_topics(bytes(data)) or []
        return [t["id"] for t in topics if t["id"] not in self.owners]

    def filter_topics(self, data, last_poster=None):
        """List payload without topics opened by blocked players, and without
        their names as a topic's last poster; None when unchanged.

        ``last_poster(topic_id)`` names who else wrote in the topic last ("" or
        None: no name is shown)."""
        data = bytes(data)
        topics = parse_topics(data)
        if topics is None:
            return None
        out = bytearray(data[:2])
        changed = False
        for t in topics:
            if self.topic_blocked(t["id"]):
                changed = True
                continue
            if self.is_blocked_name(t["name"]):
                start, end = t["name_at"]
                other = (last_poster(t["id"]) if last_poster else None) or ""
                out += data[t["start"]:start] + _pack_utf(other) + data[end:t["end"]]
                changed = True
                continue
            out += data[t["start"]:t["end"]]
        return bytes(out) if changed else None

    def is_blocked_name(self, name):
        """Blocked, also when the game wrote the name without its #tag."""
        if self.is_blocked(name):
            return True
        return "#" not in str(name or "") and _key(name) in {_base(n) for n in self.names}

    def drop_notification(self, topic_id, username):
        return self.is_blocked(username) or self.topic_blocked(topic_id)


class Favorites:
    """Café messages kept by the player, in a JSON file (newest first)."""

    def __init__(self, path=FAVORITES_PATH, clock=time.time):
        self.path = Path(path)
        self.clock = clock
        self.items = []
        try:
            self.items = list(json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass

    def save(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.items, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self.path)

    def add(self, author, text):
        author, text = str(author).strip(), str(text).strip()
        if not author or not text:
            return False
        if any(f["author"] == author and f["text"] == text for f in self.items):
            return False
        next_id = max((f["id"] for f in self.items), default=0) + 1
        self.items.insert(0, {"id": next_id, "author": author, "text": text, "saved_at": int(self.clock())})
        self.save()
        return True

    def remove(self, fav_id):
        before = len(self.items)
        self.items = [f for f in self.items if f["id"] != int(fav_id)]
        if len(self.items) == before:
            return False
        self.save()
        return True


class Watchlist:
    """Players whose new Café posts ring a bell, in a JSON file."""

    def __init__(self, path=WATCH_PATH):
        self.path = Path(path)
        self.names = {}
        try:
            self.names = {_key(n): n for n in json.loads(self.path.read_text(encoding="utf-8")) if _key(n)}
        except (OSError, ValueError, TypeError):
            pass

    def save(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(sorted(self.names.values(), key=str.lower), ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self.path)

    def toggle(self, name):
        """Watch or stop watching; True when the player is watched now."""
        key = _key(name)
        if not key:
            return False
        if self.names.pop(key, None) is None:
            self.names[key] = str(name).strip()
            self.save()
            return True
        self.save()
        return False

    def remove(self, name):
        if self.names.pop(_key(name), None) is None:
            return False
        self.save()
        return True

    def watched(self, name):
        return _key(name) in self.names


NOTES_PATH = DATA_DIR / "cafe_notes.json"
NOTE_MAX = 40


class Notes:
    """Private notes about players ("troll", "arkadaş"), in a JSON file."""

    def __init__(self, path=NOTES_PATH):
        self.path = Path(path)
        self.items = {}  # name as written -> note
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self.items = {str(k): str(v) for k, v in raw.items() if str(v).strip()}
        except (OSError, ValueError, AttributeError):
            pass

    def save(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.items, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(self.path)

    def set(self, name, text):
        name, text = str(name).strip(), " ".join(str(text).split())[:NOTE_MAX]
        if not name:
            return
        for k in [k for k in self.items if _key(k) == _key(name)]:
            del self.items[k]
        if text:
            self.items[name] = text
        self.save()

    def get(self, name):
        return next((v for k, v in self.items.items() if _key(k) == _key(name)), "")


SETTINGS_PATH = Path(__file__).resolve().parent / "cafe_settings.json"


class CafeSettings:
    """The Café extras' switches, kept in a JSON file."""

    def __init__(self, path=SETTINGS_PATH):
        self.path = Path(path)
        self.show_deleted = True  # deleted posts come back marked "(silindi)"
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self.show_deleted = bool(raw.get("show_deleted", True))
        except (OSError, ValueError, AttributeError):
            pass

    def save(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"show_deleted": self.show_deleted}, indent=1), encoding="utf-8")
        tmp.replace(self.path)

    def toggle_deleted(self):
        """Switch showing deleted posts; the new setting."""
        self.show_deleted = not self.show_deleted
        self.save()
        return self.show_deleted
