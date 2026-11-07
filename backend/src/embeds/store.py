"""SQLite persistence for embeds.

Plain sqlite3 on purpose: the schema is small, and both origins open the same
file, so there is no ORM layer to keep in sync between them.
"""

import secrets
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

Role = Literal["journalist", "model"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS embeds (
    id          TEXT PRIMARY KEY,
    journalist  TEXT NOT NULL,
    title       TEXT NOT NULL,
    created_at  TEXT NOT NULL
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

CREATE TABLE IF NOT EXISTS messages (
    embed_id        TEXT NOT NULL REFERENCES embeds (id),
    seq             INTEGER NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('journalist', 'model')),
    text            TEXT NOT NULL,
    version_number  INTEGER,
    created_at      TEXT NOT NULL,
    PRIMARY KEY (embed_id, seq)
);
"""


@dataclass(frozen=True)
class Embed:
    id: str
    journalist: str
    title: str
    created_at: str


@dataclass(frozen=True)
class Version:
    embed_id: str
    number: int
    html: str
    created_at: str


@dataclass(frozen=True)
class Message:
    embed_id: str
    seq: int
    role: Role
    text: str
    version_number: int | None
    created_at: str


def _now() -> str:
    return datetime.now(UTC).isoformat()


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

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self._path)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def create_embed(self, journalist: str, title: str) -> Embed:
        embed = Embed(
            id=new_embed_id(),
            journalist=journalist,
            title=title,
            created_at=_now(),
        )
        with self._connect() as db:
            db.execute(
                "INSERT INTO embeds (id, journalist, title, created_at) VALUES (?, ?, ?, ?)",
                (embed.id, embed.journalist, embed.title, embed.created_at),
            )
        return embed

    def embeds_of(self, journalist: str) -> list[Embed]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM embeds WHERE journalist = ? ORDER BY created_at DESC",
                (journalist,),
            ).fetchall()
        return [Embed(**row) for row in rows]

    def embed_of(self, journalist: str, embed_id: str) -> Embed | None:
        """The embed, but only if this journalist owns it."""
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM embeds WHERE id = ? AND journalist = ?", (embed_id, journalist)
            ).fetchone()
        return Embed(**row) if row else None

    def add_message(
        self, embed_id: str, role: Role, text: str, version_number: int | None = None
    ) -> Message:
        with self._connect() as db:
            (seq,) = db.execute(
                "SELECT COALESCE(MAX(seq), 0) + 1 FROM messages WHERE embed_id = ?", (embed_id,)
            ).fetchone()
            message = Message(embed_id, seq, role, text, version_number, _now())
            db.execute(
                "INSERT INTO messages VALUES (?, ?, ?, ?, ?, ?)",
                (embed_id, seq, role, text, version_number, message.created_at),
            )
        return message

    def messages_of(self, embed_id: str) -> list[Message]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM messages WHERE embed_id = ? ORDER BY seq", (embed_id,)
            ).fetchall()
        return [Message(**row) for row in rows]

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
                "SELECT * FROM versions WHERE embed_id = ? AND number = ?", (embed_id, number)
            ).fetchone()
        return Version(**row) if row else None

    def latest_version(self, embed_id: str) -> Version | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM versions WHERE embed_id = ? ORDER BY number DESC LIMIT 1",
                (embed_id,),
            ).fetchone()
        return Version(**row) if row else None
