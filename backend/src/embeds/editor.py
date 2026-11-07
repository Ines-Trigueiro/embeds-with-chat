"""The editor origin: the journalist-facing API and the built frontend."""

from pathlib import Path
from typing import Annotated, Self
from urllib.parse import unquote

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field

from embeds.config import Settings
from embeds.store import Embed, Store

STATIC_DIR = Path(__file__).parent / "static"



def journalist_name(
    x_journalist: Annotated[str, Header(min_length=1, max_length=512)],
) -> str:
    """The journalist's name, sent URL-encoded because browsers refuse non-Latin-1 headers."""
    try:
        name = unquote(x_journalist, errors="strict").strip()
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="Journalist name is not valid UTF-8") from None
    if not 1 <= len(name) <= 64:
        raise HTTPException(status_code=422, detail="Journalist name must be 1-64 characters")
    return name


Journalist = Annotated[str, Depends(journalist_name)]


class NewEmbed(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class EmbedOut(BaseModel):
    id: str
    title: str
    created_at: str

    @classmethod
    def of(cls, embed: Embed) -> Self:
        return cls(id=embed.id, title=embed.title, created_at=embed.created_at)


def create_editor_app(settings: Settings, chat_model: BaseChatModel) -> FastAPI:
    store = Store(settings.database_path)
    app = FastAPI(title="Embeds with chat – editor")

    @app.post("/api/embeds", status_code=201)
    def create_embed(body: NewEmbed, journalist: Journalist) -> EmbedOut:
        return EmbedOut.of(store.create_embed(journalist, body.title))

    @app.get("/api/embeds")
    def my_embeds(journalist: Journalist) -> list[EmbedOut]:
        return [EmbedOut.of(embed) for embed in store.embeds_of(journalist)]

    # The built React app. Mounted last so it never shadows the API routes.
    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")

    return app
