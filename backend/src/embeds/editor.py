"""The editor origin: the journalist-facing API and the built frontend."""

import json
from collections.abc import AsyncIterator
from dataclasses import replace
from pathlib import Path
from typing import Annotated, Self
from urllib.parse import unquote

from fastapi import Depends, FastAPI, Header, HTTPException, Query, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field, StringConstraints

from embeds.chat import ChatEvent, chat_turn
from embeds.config import Settings
from embeds.datasets import (
    DatasetError,
    ParsedDataset,
    is_dataset_file,
    parse_dataset,
    without_dataset_contents,
)
from embeds.delivery import EMBED_ID, embed_url, snippet, test_article_page
from embeds.images import image_type, image_url
from embeds.languages import Language
from embeds.previews import Previews
from embeds.quality_check import Finding, Severity, check, has_blockers
from embeds.store import (
    Attachment,
    AttachmentKind,
    Embed,
    Message,
    MessageKind,
    Role,
    Store,
    Version,
)

MAX_ATTACHMENT_BYTES = 5_000_000

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


Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class NewEmbed(BaseModel):
    title: Title | None = None  # Left out, it is suggested from the first message.
    embed_language: Language = "nb"


class EmbedChanges(BaseModel):
    """Only the fields that are sent change."""

    embed_language: Language | None = None
    title: Title | None = None


class EmbedOut(BaseModel):
    id: str
    title: str | None  # None until suggested from the journalist's first message.
    created_at: str
    embed_language: Language
    published: bool  # Whether any version is published.

    @classmethod
    def of(cls, embed: Embed, published: bool) -> Self:
        return cls(
            id=embed.id,
            title=embed.title,
            created_at=embed.created_at,
            embed_language=embed.embed_language,
            published=published,
        )


class NewTranslation(BaseModel):
    embed_language: Language  # The language to translate the current version into.
    language: Language = "nb"  # The journalist's chat language.


class NewMessage(BaseModel):
    content: str = Field(min_length=1, max_length=10_000)
    language: Language = "nb"  # The journalist's chat language.


class Delivery(BaseModel):
    """What the journalist pastes into an article."""

    snippet: str
    embed_url: str


class FindingOut(BaseModel):
    rule: str
    severity: Severity
    detail: str

    @classmethod
    def of(cls, finding: Finding) -> Self:
        return cls(rule=finding.rule, severity=finding.severity, detail=finding.detail)


class VersionOut(BaseModel):
    number: int
    created_at: str
    preview_url: str
    published: bool
    delivery: Delivery | None  # Pinned to this version; only once it is published.
    findings: list[FindingOut]  # From the quality check.


class MessageOut(BaseModel):
    role: Role
    kind: MessageKind  # A translation's text is the language it translated into.
    text: str
    version_number: int | None
    guides: list[str]

    @classmethod
    def of(cls, message: Message) -> Self:
        return cls(
            role=message.role,
            kind=message.kind,
            text=message.text,
            version_number=message.version_number,
            guides=list(message.guides),
        )


class ColumnOut(BaseModel):
    name: str
    type: str


class AttachmentOut(BaseModel):
    id: str
    kind: AttachmentKind
    name: str
    created_at: str
    rows: int | None = None  # Datasets only.
    columns: list[ColumnOut] | None = None  # Datasets only.
    url: str | None = None  # Images only: where the embed can show it.

    @classmethod
    def of(cls, attachment: Attachment, embed_origin: str) -> Self:
        out = cls(
            id=attachment.id,
            kind=attachment.kind,
            name=attachment.name,
            created_at=attachment.created_at,
        )
        if attachment.kind == "image":
            out.url = image_url(embed_origin, attachment.embed_id, attachment.id)
        if attachment.kind == "dataset":
            dataset = ParsedDataset.from_bytes(attachment.content)
            out.rows = len(dataset.rows)
            out.columns = [ColumnOut(name=c.name, type=c.type) for c in dataset.columns]
        return out


class OpenedEmbed(EmbedOut):
    messages: list[MessageOut]
    attachments: list[AttachmentOut]
    versions: list[VersionOut]
    latest_version: VersionOut | None
    progress_frame_url: str
    delivery: Delivery | None  # Follows the newest published version; once one exists.


def create_editor_app(settings: Settings, chat_model: BaseChatModel) -> FastAPI:
    store = Store(settings.database_path)
    previews = Previews.from_settings(settings)
    app = FastAPI(title="Embeds with chat – editor")

    origin = settings.embed_origin

    def delivery(embed_id: str, number: int | None = None) -> Delivery:
        return Delivery(
            snippet=snippet(origin, embed_id, number),
            embed_url=embed_url(origin, embed_id, number),
        )

    def quality_findings(version: Version) -> list[Finding]:
        return check(without_dataset_contents(version.html), origin)

    def version_out(version: Version, published: bool) -> VersionOut:
        embed_id, number = version.embed_id, version.number
        return VersionOut(
            number=number,
            created_at=version.created_at,
            preview_url=previews.url(embed_id, number),
            published=published,
            delivery=delivery(embed_id, number) if published else None,
            findings=[FindingOut.of(f) for f in quality_findings(version)],
        )

    def opened(embed: Embed) -> OpenedEmbed:
        published = store.published_numbers(embed.id)
        versions = [version_out(v, v.number in published) for v in store.versions_of(embed.id)]
        return OpenedEmbed(
            **EmbedOut.of(embed, bool(published)).model_dump(),
            messages=[MessageOut.of(m) for m in store.messages_of(embed.id)],
            attachments=[AttachmentOut.of(a, origin) for a in store.attachments_of(embed.id)],
            versions=versions,
            latest_version=versions[-1] if versions else None,
            progress_frame_url=f"{origin}/progress-frame",
            delivery=delivery(embed.id) if published else None,
        )

    def owned_embed(embed_id: str, journalist: str) -> Embed:
        embed = store.embed_of(journalist, embed_id)
        if embed is None:
            raise HTTPException(status_code=404, detail="No such embed")
        return embed

    @app.post("/api/embeds", status_code=201)
    def create_embed(body: NewEmbed, journalist: Journalist) -> EmbedOut:
        return EmbedOut.of(store.create_embed(journalist, body.title, body.embed_language), False)

    @app.get("/api/embeds")
    def my_embeds(journalist: Journalist) -> list[EmbedOut]:
        published = store.published_embed_ids(journalist)
        return [EmbedOut.of(embed, embed.id in published) for embed in store.embeds_of(journalist)]

    @app.get("/api/embeds/{embed_id}")
    def open_embed(embed_id: str, journalist: Journalist) -> OpenedEmbed:
        return opened(owned_embed(embed_id, journalist))

    @app.post("/api/embeds/{embed_id}/versions/{number}/publish")
    def publish(
        embed_id: str, number: int, journalist: Journalist, accept_warnings: bool = False
    ) -> OpenedEmbed:
        """Publish, gated by the quality check: blockers refuse, warnings need confirming."""
        embed = owned_embed(embed_id, journalist)
        version = store.version(embed_id, number)
        if version is None:
            raise HTTPException(status_code=404, detail="No such version")
        findings = quality_findings(version)
        blocked = has_blockers(findings)
        if blocked or (findings and not accept_warnings):
            raise HTTPException(
                status_code=422 if blocked else 409,
                detail={"findings": [FindingOut.of(f).model_dump() for f in findings]},
            )
        store.publish(embed_id, number)
        return opened(embed)

    @app.post("/api/embeds/{embed_id}/attachments", status_code=201)
    async def attach(embed_id: str, file: UploadFile, journalist: Journalist) -> AttachmentOut:
        """Attach a Dataset (.csv, .xlsx) or an Image. Each one is a new attachment."""
        owned_embed(embed_id, journalist)
        name = (file.filename or "attachment").strip()[:200]
        content = await file.read(MAX_ATTACHMENT_BYTES + 1)
        if len(content) > MAX_ATTACHMENT_BYTES:
            limit = MAX_ATTACHMENT_BYTES // 1_000_000
            raise HTTPException(status_code=422, detail=f"The file is larger than {limit} MB.")
        if media_type := image_type(content):
            image = store.add_attachment(embed_id, "image", name, media_type, content)
            return AttachmentOut.of(image, origin)
        if not is_dataset_file(name):
            raise HTTPException(
                status_code=422,
                detail="Attach a spreadsheet (.csv, .xlsx) or an image (PNG, JPEG, GIF, WebP).",
            )
        try:
            dataset = parse_dataset(name, content)
        except DatasetError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        attachment = store.add_attachment(
            embed_id, "dataset", name, "application/json", dataset.to_bytes()
        )
        return AttachmentOut.of(attachment, origin)

    @app.patch("/api/embeds/{embed_id}")
    def change_embed(embed_id: str, body: EmbedChanges, journalist: Journalist) -> EmbedOut:
        embed = owned_embed(embed_id, journalist)
        if body.embed_language is not None:
            store.set_embed_language(embed_id, body.embed_language)
            embed = replace(embed, embed_language=body.embed_language)
        if body.title is not None:
            store.set_title(embed_id, body.title)
            embed = replace(embed, title=body.title)
        return EmbedOut.of(embed, bool(store.published_numbers(embed_id)))

    def streamed(turn: AsyncIterator[ChatEvent]) -> StreamingResponse:
        async def server_sent_events() -> AsyncIterator[str]:
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

    @app.post("/api/embeds/{embed_id}/messages")
    def send_message(embed_id: str, body: NewMessage, journalist: Journalist) -> StreamingResponse:
        embed = owned_embed(embed_id, journalist)
        return streamed(
            chat_turn(store, chat_model, embed, body.content, body.language, settings.embed_origin)
        )

    @app.post("/api/embeds/{embed_id}/translations")
    def translate(embed_id: str, body: NewTranslation, journalist: Journalist) -> StreamingResponse:
        """A Translation (ADR 0004): the current version, rewritten into a new embed language."""
        embed = owned_embed(embed_id, journalist)
        if store.latest_version(embed_id) is None:
            raise HTTPException(status_code=409, detail="There is no version to translate yet.")
        if body.embed_language == embed.embed_language:
            raise HTTPException(status_code=409, detail="The embed is already in that language.")
        # Stored only once the translated version exists: a failed one changes nothing.
        embed = replace(embed, embed_language=body.embed_language)
        return streamed(
            chat_turn(
                store, chat_model, embed, "", body.language, settings.embed_origin, translation=True
            )
        )

    @app.get("/test-article", response_class=HTMLResponse)
    def test_article(
        embed: Annotated[str, Query(pattern=EMBED_ID.pattern)],
        version: Annotated[int | None, Query(ge=1)] = None,
    ) -> str:
        """A stand-in article page that shows an embed through its Snippet."""
        return test_article_page(origin, embed, version)

    # The built React app. Mounted last so it never shadows the API routes.
    if STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")

    return app
