"""The editor origin: the journalist-facing API and the built frontend."""

from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Header
from fastapi.staticfiles import StaticFiles
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field

from embeds.config import Settings
from embeds.store import Store

STATIC_DIR = Path(__file__).parent / "static"

Journalist = Annotated[str, Header(alias="X-Journalist", min_length=1, max_length=64)]


class NewEmbed(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class EmbedOut(BaseModel):
    id: str
    title: str
    created_at: str


def create_editor_app(settings: Settings, chat_model: BaseChatModel) -> FastAPI:
    store = Store(settings.database_path)
    app = FastAPI(title="Embeds with chat – editor")

    @app.post("/api/embeds", status_code=201)
    def create_embed(body: NewEmbed, journalist: Journalist) -> EmbedOut:
        embed = store.create_embed(journalist, body.title)
        return EmbedOut(id=embed.id, title=embed.title, created_at=embed.created_at)

    @app.get("/api/embeds")
    def my_embeds(journalist: Journalist) -> list[EmbedOut]:
        return [
            EmbedOut(id=e.id, title=e.title, created_at=e.created_at)
            for e in store.embeds_of(journalist)
        ]

    # The built React app. Mounted last so it never shadows the API routes.
    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")

    return app
