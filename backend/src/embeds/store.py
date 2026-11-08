"""SQLite persistence for embeds.

Plain sqlite3 on purpose: the schema is small, and both origins open the same
file, so there is no ORM layer to keep in sync between them.
"""

import json
import secrets
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from embeds.languages import Language

Role = Literal["journalist", "model"]
# A Translation is asked for by the tool, not typed: its text is the new embed language.
MessageKind = Literal["message", "translation"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS embeds (
    id              TEXT PRIMARY KEY,
    journalist      TEXT NOT NULL,
    title           TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    embed_language  TEXT NOT NULL DEFAULT 'nb'
);
CREATE INDEX IF NOT EXISTS embeds_by_journalist ON embeds (journalist, created_at);

-- Versions are immutable: rows are inserted, never updated (ADR 0003).
CREATE TABLE IF NOT EXISTS versions (
    embed_id    TEXT NOT NULL REFERENCES embeds (id),
    number      INTEGER NOT NULL,
    html        TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    PRIMARY KEY (embed_id, number)
);

-- A version is published when it has a row here; publishing never changes the version.
CREATE TABLE IF NOT EXISTS publications (
    embed_id      TEXT NOT NULL,
    number        INTEGER NOT NULL,
    published_at  TEXT NOT NULL,
    PRIMARY KEY (embed_id, number),
    FOREIGN KEY (embed_id, number) REFERENCES versions (embed_id, number)
);

-- What the journalist attached to an embed: datasets and images. Never changed.
CREATE TABLE IF NOT EXISTS attachments (
    id          TEXT PRIMARY KEY,
    embed_id    TEXT NOT NULL REFERENCES embeds (id),
    kind        TEXT NOT NULL CHECK (kind IN ('dataset', 'image')),
    name        TEXT NOT NULL,
    media_type  TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    content     BLOB NOT NULL  -- a dataset's parsed rows as JSON, or an image's bytes
);

CREATE TABLE IF NOT EXISTS messages (
    embed_id        TEXT NOT NULL REFERENCES embeds (id),
    seq             INTEGER NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('journalist', 'model')),
    text            TEXT NOT NULL,
    version_number  INTEGER,
    created_at      TEXT NOT NULL,
    guides          TEXT NOT NULL DEFAULT '[]',  -- JSON list of the guides the model read
    kind            TEXT NOT NULL DEFAULT 'message' CHECK (kind IN ('message', 'translation')),
    PRIMARY KEY (embed_id, seq)
);
"""


# Columns added after the first release, for databases created before them.
MIGRATIONS = {
    ("embeds", "embed_language"): "ALTER TABLE embeds ADD COLUMN embed_language TEXT NOT NULL DEFAULT 'nb'",
    ("messages", "guides"): "ALTER TABLE messages ADD COLUMN guides TEXT NOT NULL DEFAULT '[]'",
    ("messages", "kind"): "ALTER TABLE messages ADD COLUMN kind TEXT NOT NULL DEFAULT 'message'",
}


@dataclass(frozen=True)
class Embed:
    id: str
    journalist: str
    title: str | None  # None until one is suggested from the journalist's first message.
    created_at: str
    embed_language: Language
    published: bool = False  # Whether any of its versions is published.


@dataclass(frozen=True)
class Version:
    embed_id: str
    number: int
    html: str
    created_at: str
    published: bool = False


@dataclass(frozen=True)
class Message:
    embed_id: str
    seq: int
    role: Role
    text: str
    version_number: int | None
    created_at: str
    guides: tuple[str, ...] = ()
    kind: MessageKind = "message"


AttachmentKind = Literal["dataset", "image"]


@dataclass(frozen=True)
class Attachment:
    id: str
    embed_id: str
    kind: AttachmentKind
    name: str
    media_type: str
    created_at: str
    content: bytes


def _now() -> str:
    return datetime.now(UTC).isoformat()


# Rows come back with their publication state, so callers never look it up separately.
EMBEDS = (
    "SELECT e.*, EXISTS (SELECT 1 FROM publications p WHERE p.embed_id = e.id) AS published"
    " FROM embeds e"
)
VERSIONS = (
    "SELECT v.*, p.number IS NOT NULL AS published"
    " FROM versions v LEFT JOIN publications p USING (embed_id, number)"
)


def _embed(row: sqlite3.Row) -> Embed:
    return Embed(**{**dict(row), "title": row["title"] or None, "published": bool(row["published"])})


def _version(row: sqlite3.Row) -> Version:
    return Version(**{**dict(row), "published": bool(row["published"])})


def new_embed_id() -> str:
    """Short, random and unguessable, so versions that are not published can't be found by guessing."""
    return secrets.token_urlsafe(9)


class Store:
    def __init__(self, path: Path) -> None:
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript(SCHEMA)
            for (table, column), statement in MIGRATIONS.items():
                columns = {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}
                if column not in columns:
                    db.execute(statement)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self._path)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def create_embed(self, journalist: str, title: str | None, embed_language: Language) -> Embed:
        embed = Embed(new_embed_id(), journalist, title, _now(), embed_language)
        with self._connect() as db:
            db.execute(
                "INSERT INTO embeds (id, journalist, title, created_at, embed_language)"
                " VALUES (?, ?, ?, ?, ?)",
                # The column predates optional titles, so "no title yet" is stored as ''.
                (embed.id, embed.journalist, embed.title or "", embed.created_at, embed_language),
            )
        return embed

    def set_title(self, embed_id: str, title: str) -> None:
        with self._connect() as db:
            db.execute("UPDATE embeds SET title = ? WHERE id = ?", (title, embed_id))

    def set_embed_language(self, embed_id: str, embed_language: Language) -> None:
        with self._connect() as db:
            db.execute("UPDATE embeds SET embed_language = ? WHERE id = ?", (embed_language, embed_id))

    def embeds_of(self, journalist: str) -> list[Embed]:
        with self._connect() as db:
            rows = db.execute(
                f"{EMBEDS} WHERE e.journalist = ? ORDER BY e.created_at DESC",
                (journalist,),
            ).fetchall()
        return [_embed(row) for row in rows]

    def embed_of(self, journalist: str, embed_id: str) -> Embed | None:
        """The embed, but only if this journalist owns it."""
        with self._connect() as db:
            row = db.execute(
                f"{EMBEDS} WHERE e.id = ? AND e.journalist = ?", (embed_id, journalist)
            ).fetchone()
        return _embed(row) if row else None

    def add_message(
        self,
        embed_id: str,
        role: Role,
        text: str,
        version_number: int | None = None,
        guides: tuple[str, ...] = (),
        kind: MessageKind = "message",
    ) -> Message:
        with self._connect() as db:
            (seq,) = db.execute(
                "SELECT COALESCE(MAX(seq), 0) + 1 FROM messages WHERE embed_id = ?", (embed_id,)
            ).fetchone()
            message = Message(embed_id, seq, role, text, version_number, _now(), guides, kind)
            db.execute(
                "INSERT INTO messages"
                " (embed_id, seq, role, text, version_number, created_at, guides, kind)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (embed_id, seq, role, text, version_number, message.created_at, json.dumps(guides), kind),
            )
        return message

    def messages_of(self, embed_id: str) -> list[Message]:
        """The embed's conversation, oldest first."""
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM messages WHERE embed_id = ? ORDER BY seq", (embed_id,)
            ).fetchall()
        return [
            Message(**{**dict(row), "guides": tuple(json.loads(row["guides"]))}) for row in rows
        ]

    def add_version(self, embed_id: str, html: str) -> Version:
        with self._connect() as db:
            (number,) = db.execute(
                "SELECT COALESCE(MAX(number), 0) + 1 FROM versions WHERE embed_id = ?", (embed_id,)
            ).fetchone()
            version = Version(embed_id, number, html, _now())
            db.execute(
                "INSERT INTO versions VALUES (?, ?, ?, ?)",
                (embed_id, number, html, version.created_at),
            )
        return version

    def version(self, embed_id: str, number: int) -> Version | None:
        with self._connect() as db:
            row = db.execute(
                f"{VERSIONS} WHERE v.embed_id = ? AND v.number = ?", (embed_id, number)
            ).fetchone()
        return _version(row) if row else None

    def latest_version(self, embed_id: str) -> Version | None:
        with self._connect() as db:
            row = db.execute(
                f"{VERSIONS} WHERE v.embed_id = ? ORDER BY v.number DESC LIMIT 1", (embed_id,)
            ).fetchone()
        return _version(row) if row else None

    def versions_of(self, embed_id: str) -> list[Version]:
        with self._connect() as db:
            rows = db.execute(
                f"{VERSIONS} WHERE v.embed_id = ? ORDER BY v.number", (embed_id,)
            ).fetchall()
        return [_version(row) for row in rows]

    def version_for_readers(self, embed_id: str, number: int | None = None) -> Version | None:
        """The latest published version, or the pinned one if it is published (ADR 0003)."""
        with self._connect() as db:
            row = db.execute(
                f"{VERSIONS} WHERE v.embed_id = ? AND p.number IS NOT NULL"
                " AND (? IS NULL OR v.number = ?) ORDER BY v.number DESC LIMIT 1",
                (embed_id, number, number),
            ).fetchone()
        return _version(row) if row else None

    def publish(self, embed_id: str, number: int) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO publications VALUES (?, ?, ?)", (embed_id, number, _now())
            )

    def add_attachment(
        self, embed_id: str, kind: AttachmentKind, name: str, media_type: str, content: bytes
    ) -> Attachment:
        # 128 random bits: image URLs are public, so they must not be guessable.
        attachment = Attachment(
            secrets.token_urlsafe(16), embed_id, kind, name, media_type, _now(), content
        )
        with self._connect() as db:
            db.execute(
                "INSERT INTO attachments VALUES (?, ?, ?, ?, ?, ?, ?)",
                (attachment.id, embed_id, kind, name, media_type, attachment.created_at, content),
            )
        return attachment

    def attachment(self, embed_id: str, attachment_id: str) -> Attachment | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM attachments WHERE embed_id = ? AND id = ?", (embed_id, attachment_id)
            ).fetchone()
        return Attachment(**row) if row else None

    def attachments_of(self, embed_id: str) -> list[Attachment]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM attachments WHERE embed_id = ? ORDER BY created_at", (embed_id,)
            ).fetchall()
        return [Attachment(**row) for row in rows]
