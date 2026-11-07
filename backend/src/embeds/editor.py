"""The editor origin: the journalist-facing API and the built frontend."""

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated, Self
from urllib.parse import unquote

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field

from embeds.chat import chat_turn
from embeds.config import Settings
from embeds.delivery import embed_url, snippet, test_article_page
from embeds.languages import Language
from embeds.previews import Previews
from embeds.store import Embed, Message, Role, Store, Version

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
    embed_language: Language = "nb"


class EmbedChanges(BaseModel):
    embed_language: Language


class EmbedOut(BaseModel):
    id: str
    title: str
    created_at: str
    embed_language: Language

    @classmethod
    def of(cls, embed: Embed) -> Self:
        return cls(
            id=embed.id,
            title=embed.title,
            created_at=embed.created_at,
            embed_language=embed.embed_language,
        )


class NewMessage(BaseModel):
    content: str = Field(min_length=1, max_length=10_000)
    language: Language = "nb"  # The journalist's chat language.


class VersionOut(BaseModel):
    number: int
    created_at: str
    preview_url: str
    published: bool
    # Pinned to this version; only once it is published.
    embed_url: str | None
    snippet: str | None


class MessageOut(BaseModel):
    role: Role
    text: str
    version_number: int | None

    @classmethod
    def of(cls, message: Message) -> Self:
        return cls(role=message.role, text=message.text, version_number=message.version_number)


class OpenedEmbed(EmbedOut):
    messages: list[MessageOut]
    versions: list[VersionOut]
    latest_version: VersionOut | None
    progress_frame_url: str
    # Follow the newest published version; only once something is published.
    embed_url: str | None
    snippet: str | None


def create_editor_app(settings: Settings, chat_model: BaseChatModel) -> FastAPI:
    store = Store(settings.database_path)
    previews = Previews.from_settings(settings)
    app = FastAPI(title="Embeds with chat – editor")

    origin = settings.embed_origin

    def version_out(version: Version, published: bool) -> VersionOut:
        embed_id, number = version.embed_id, version.number
        return VersionOut(
            number=number,
            created_at=version.created_at,
            preview_url=previews.url(embed_id, number),
            published=published,
            embed_url=embed_url(origin, embed_id, number) if published else None,
            snippet=snippet(origin, embed_id, number) if published else None,
        )

    def opened(embed: Embed) -> OpenedEmbed:
        published = store.published_numbers(embed.id)
        versions = [version_out(v, v.number in published) for v in store.versions_of(embed.id)]
        return OpenedEmbed(
            **EmbedOut.of(embed).model_dump(),
            messages=[MessageOut.of(m) for m in store.messages_of(embed.id)],
            versions=versions,
            latest_version=versions[-1] if versions else None,
            progress_frame_url=f"{origin}/progress-frame",
            embed_url=embed_url(origin, embed.id) if published else None,
            snippet=snippet(origin, embed.id) if published else None,
        )

    def owned_embed(embed_id: str, journalist: str) -> Embed:
        embed = store.embed_of(journalist, embed_id)
        if embed is None:
            raise HTTPException(status_code=404, detail="No such embed")
        return embed

    @app.post("/api/embeds", status_code=201)
    def create_embed(body: NewEmbed, journalist: Journalist) -> EmbedOut:
        return EmbedOut.of(store.create_embed(journalist, body.title, body.embed_language))

    @app.get("/api/embeds")
    def my_embeds(journalist: Journalist) -> list[EmbedOut]:
        return [EmbedOut.of(embed) for embed in store.embeds_of(journalist)]

    @app.get("/api/embeds/{embed_id}")
    def open_embed(embed_id: str, journalist: Journalist) -> OpenedEmbed:
        return opened(owned_embed(embed_id, journalist))

    @app.post("/api/embeds/{embed_id}/versions/{number}/publish")
    def publish(embed_id: str, number: int, journalist: Journalist) -> OpenedEmbed:
        embed = owned_embed(embed_id, journalist)
        if store.version(embed_id, number) is None:
            raise HTTPException(status_code=404, detail="No such version")
        store.publish(embed_id, number)
        return opened(embed)

    @app.patch("/api/embeds/{embed_id}")
    def change_embed(embed_id: str, body: EmbedChanges, journalist: Journalist) -> EmbedOut:
        owned_embed(embed_id, journalist)
        store.set_embed_language(embed_id, body.embed_language)
        return EmbedOut.of(owned_embed(embed_id, journalist))

    @app.post("/api/embeds/{embed_id}/messages")
    def send_message(embed_id: str, body: NewMessage, journalist: Journalist) -> StreamingResponse:
        embed = owned_embed(embed_id, journalist)

        async def server_sent_events() -> AsyncIterator[str]:
            turn = chat_turn(
                store, chat_model, embed, body.content, body.language, settings.embed_origin
            )
            async for event, data in turn:
                if isinstance(data, Version):
                    payload = version_out(data, published=False).model_dump()
                else:
                    payload = data
                yield f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            server_sent_events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    @app.get("/test-article", response_class=HTMLResponse)
    def test_article(
        embed: Annotated[str, Query(pattern=r"^[A-Za-z0-9_-]{1,64}$")],
        version: Annotated[int | None, Query(ge=1)] = None,
    ) -> str:
        """A stand-in article page that shows an embed through its Snippet."""
        return test_article_page(origin, embed, version)

    # The built React app. Mounted last so it never shadows the API routes.
    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")

    return app
