"""Every Café post this client has seen, kept in SQLite and searchable.

transformice/cafe_archive.sqlite3 (not committed). The proxy adds the posts of
every topic it sees (the player's own and the ones it asks about in the
background) and the topic titles of the list.

Search: words must all appear in the text; a word starting with @ picks the
author instead ("@Eby çay" = Eby's posts with "çay"). Case does not matter,
Turkish İ/I included.
"""

import re
import sqlite3
import time
from pathlib import Path

from .paths import DATA_DIR

ARCHIVE_PATH = DATA_DIR / "cafe_archive.sqlite3"
SEARCH_LIMIT = 60


def fold(text):
    """Lower case the Turkish way (I -> ı, İ -> i)."""
    return str(text or "").replace("I", "ı").replace("İ", "i").lower()


def _base(name):
    return fold(name).split("#", 1)[0]


def mentions(text, me):
    """True when the text names the player (@Name) or quotes them."""
    base = _base(me)
    if not base:
        return False
    return re.search(r"@" + re.escape(base) + r"(?![\w])", fold(text)) is not None


class Archive:
    def __init__(self, path=ARCHIVE_PATH, clock=time.time):
        self.clock = clock
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS posts (
                post_id INTEGER PRIMARY KEY, topic_id INTEGER, author TEXT, author_fold TEXT,
                text TEXT, text_fold TEXT, avatar INTEGER, seen_at INTEGER);
            CREATE INDEX IF NOT EXISTS posts_topic ON posts(topic_id);
            CREATE INDEX IF NOT EXISTS posts_author ON posts(author_fold);
            CREATE TABLE IF NOT EXISTS topics (topic_id INTEGER PRIMARY KEY, title TEXT);
        """)

    def has_topic(self, topic_id):
        return self.db.execute("SELECT 1 FROM posts WHERE topic_id = ? LIMIT 1", (topic_id,)).fetchone() is not None

    def add_posts(self, topic_id, posts):
        """Store posts; the ones not seen before."""
        known = {row[0] for row in self.db.execute(
            "SELECT post_id FROM posts WHERE topic_id = ?", (topic_id,))}
        new = [p for p in posts if p["post_id"] not in known]
        now = int(self.clock())
        with self.db:
            self.db.executemany(
                "INSERT OR REPLACE INTO posts VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT seen_at FROM posts WHERE post_id = ?), ?))",
                [(p["post_id"], topic_id, p["author"], fold(p["author"]), p["text"], fold(p["text"]),
                  p.get("avatar") or 0, p["post_id"], now) for p in posts])
        return new

    def add_topics(self, topics):
        with self.db:
            self.db.executemany("INSERT OR REPLACE INTO topics VALUES (?, ?)", [(t["id"], t["title"]) for t in topics])

    def title(self, topic_id):
        row = self.db.execute("SELECT title FROM topics WHERE topic_id = ?", (topic_id,)).fetchone()
        return row[0] if row else ""

    def search(self, query, limit=SEARCH_LIMIT):
        words, authors = [], []
        for word in str(query or "").split():
            (authors if word.startswith("@") and len(word) > 1 else words).append(fold(word.lstrip("@") if word.startswith("@") else word))
        if not words and not authors:
            return []
        where, args = [], []
        for w in words:
            where.append("p.text_fold LIKE ? ESCAPE '\\'")
            args.append("%" + w.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%")
        for a in authors:
            where.append("p.author_fold LIKE ? ESCAPE '\\'")
            args.append(a.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%")
        rows = self.db.execute(
            "SELECT p.author, p.text, COALESCE(t.title, ''), p.topic_id, p.seen_at, p.post_id, p.avatar FROM posts p "
            "LEFT JOIN topics t ON t.topic_id = p.topic_id WHERE " + " AND ".join(where) +
            " ORDER BY p.post_id DESC LIMIT ?", args + [limit]).fetchall()
        return [{"author": r[0], "text": r[1], "title": r[2], "topic": r[3], "seen_at": r[4], "post": r[5],
                 "avatar": r[6]} for r in rows]

    def find(self, author, text):
        """The newest archived post of this author with this text (whitespace aside), or None."""
        want = " ".join(str(text or "").split())
        for r in self.db.execute(
                "SELECT p.post_id, p.topic_id, p.avatar, p.text, COALESCE(t.title, '') FROM posts p "
                "LEFT JOIN topics t ON t.topic_id = p.topic_id WHERE p.author_fold = ? ORDER BY p.post_id DESC",
                (fold(author),)):
            if " ".join(r[3].split()) == want:
                return {"post": r[0], "topic": r[1], "avatar": r[2], "title": r[4], "text": r[3]}
        return None

    def last_author(self, topic_id, skip=lambda name: False):
        """Who wrote the topic's newest archived post, leaving out ``skip``ped names."""
        for (author,) in self.db.execute(
                "SELECT author FROM posts WHERE topic_id = ? ORDER BY post_id DESC", (int(topic_id),)):
            if not skip(author):
                return author
        return None

    def count(self):
        return self.db.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
