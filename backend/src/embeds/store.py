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

SCHEMA = """
CREATE TABLE IF NOT EXISTS embeds (
    id          TEXT PRIMARY KEY,
    journalist  TEXT NOT NULL,
    title       TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS embeds_by_journalist ON embeds (journalist, created_at);
"""


@dataclass(frozen=True)
class Embed:
    id: str
    journalist: str
    title: str
    created_at: str


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
            created_at=datetime.now(UTC).isoformat(),
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
