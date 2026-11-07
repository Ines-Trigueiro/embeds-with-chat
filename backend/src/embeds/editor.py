"""The editor origin: the journalist-facing API and the built frontend."""

from pathlib import Path
from typing import Annotated, Self
from urllib.parse import unquote

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field

from embeds.chat import chat_turn
from embeds.config import Settings
from embeds.previews import PreviewSigner, load_or_create_secret
from embeds.store import Embed, Message, Store, Version

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


class NewMessage(BaseModel):
    content: str = Field(min_length=1, max_length=10_000)


class VersionOut(BaseModel):
    number: int
    created_at: str
    preview_url: str


class MessageOut(BaseModel):
    role: str
    text: str
    version_number: int | None

    @classmethod
    def of(cls, message: Message) -> Self:
        return cls(role=message.role, text=message.text, version_number=message.version_number)


class OpenedEmbed(EmbedOut):
    messages: list[MessageOut]
    latest_version: VersionOut | None
    draft_frame_url: str


def create_editor_app(settings: Settings, chat_model: BaseChatModel) -> FastAPI:
    store = Store(settings.database_path)
    signer = PreviewSigner(load_or_create_secret(settings.data_dir))
    app = FastAPI(title="Embeds with chat – editor")

    def describe(version: Version) -> VersionOut:
        sig = signer.sign(version.embed_id, version.number)
        return VersionOut(
            number=version.number,
            created_at=version.created_at,
            preview_url=f"{settings.embed_origin}/preview/{version.embed_id}/{version.number}?sig={sig}",
        )

    def owned_embed(embed_id: str, journalist: str) -> Embed:
        embed = store.embed_of(journalist, embed_id)
        if embed is None:
            raise HTTPException(status_code=404, detail="No such embed")
        return embed

    @app.post("/api/embeds", status_code=201)
    def create_embed(body: NewEmbed, journalist: Journalist) -> EmbedOut:
        return EmbedOut.of(store.create_embed(journalist, body.title))

    @app.get("/api/embeds")
    def my_embeds(journalist: Journalist) -> list[EmbedOut]:
        return [EmbedOut.of(embed) for embed in store.embeds_of(journalist)]

    @app.get("/api/embeds/{embed_id}")
    def open_embed(embed_id: str, journalist: Journalist) -> OpenedEmbed:
        embed = owned_embed(embed_id, journalist)
        latest = store.latest_version(embed_id)
        return OpenedEmbed(
            **EmbedOut.of(embed).model_dump(),
            messages=[MessageOut.of(m) for m in store.messages_of(embed_id)],
            latest_version=describe(latest) if latest else None,
            draft_frame_url=f"{settings.embed_origin}/draft-frame",
        )

    @app.post("/api/embeds/{embed_id}/messages")
    def send_message(embed_id: str, body: NewMessage, journalist: Journalist) -> StreamingResponse:
        owned_embed(embed_id, journalist)
        events = chat_turn(
            store, chat_model, embed_id, body.content, lambda v: describe(v).model_dump()
        )
        return StreamingResponse(
            events,
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    # The built React app. Mounted last so it never shadows the API routes.
    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")

    return app
