"""One chat turn: stream the model's reply as events, and keep the result.

Events, in order:
- `title`    {"title"}        the embed's suggested Title (first message of an untitled embed only)
- `guide`    {"name"}         the model is reading a guide (zero or more)
- `text`     {"delta"}        prose for the chat, as it arrives
- `progress` {"html"}         the work in progress, at most about once a second
- `version`  Version          a new Version was created from the finished reply
- `error`    {"message"}      the reply broke the contract or the model failed; no Version
- `done`     {"text"}         the final chat text of the model's message
"""

import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field, replace
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, ToolMessage

from embeds.context import turn_context
from embeds.datasets import DatasetAttachment, ParsedDataset, inject_datasets
from embeds.guides import LOAD_GUIDE_TOOL, base_guide, load_guide
from embeds.images import MAX_IMAGES_FOR_MODEL, ImageForModel, image_url
from embeds.languages import Language, translation_request, with_document_language
from embeds.reply import ReplyError, ReplyStream, parse_reply, prose_before_html
from embeds.store import Embed, Store, Version
from embeds.titles import suggest_title

PROGRESS_INTERVAL_SECONDS = 1.0
MAX_GUIDE_ROUNDS = 3
MODEL_UNAVAILABLE = "Sorry, I couldn't answer just now. Please try again."
NO_TRANSLATION = "The model replied without a translated version. Please try again."

ChatEvent = tuple[str, dict[str, Any] | Version]


async def chat_turn(
    store: Store,
    model: BaseChatModel,
    embed: Embed,
    content: str,
    chat_language: Language,
    embed_origin: str,
) -> AsyncIterator[ChatEvent]:
    """The journalist's message, and the model's reply to it."""
    if embed.title is None:
        # Before the reply, so the sidebar can name the embed while the journalist waits.
        title = await suggest_title(model, content)
        store.set_title(embed.id, title)
        yield "title", {"title": title}
    request = _Request.of(store, embed, content, chat_language, embed_origin)
    store.add_message(embed.id, "journalist", content)
    reply = _Reply()
    async for event in _model_reply(model, request, reply):
        yield event
    version = store.add_version(embed.id, reply.html) if reply.html else None
    number = version.number if version else None
    store.add_message(embed.id, "model", reply.text, number, tuple(reply.guides))
    for event in _ending(reply, version):
        yield event


async def translation_turn(
    store: Store,
    model: BaseChatModel,
    embed: Embed,
    language: Language,
    chat_language: Language,
    embed_origin: str,
) -> AsyncIterator[ChatEvent]:
    """A Translation (ADR 0004): the journalist typed nothing; the current version is
    rewritten into `language`. Only one that produced a version is kept: the marker, the
    new embed language and the reply. A failed one leaves no trace."""
    embed = replace(embed, embed_language=language)
    request = _Request.of(store, embed, translation_request(language), chat_language, embed_origin)
    reply = _Reply()
    async for event in _model_reply(model, request, reply):
        yield event
    version = None
    if reply.html is None:
        reply.error = reply.error or NO_TRANSLATION
        reply.text = reply.text or NO_TRANSLATION
    else:
        store.add_message(embed.id, "journalist", language, kind="translation")
        store.set_embed_language(embed.id, language)
        version = store.add_version(embed.id, reply.html)
        store.add_message(embed.id, "model", reply.text, version.number, tuple(reply.guides))
    for event in _ending(reply, version):
        yield event


@dataclass(frozen=True)
class _Request:
    """One turn's request to the model, and what its reply needs to become a Version."""

    messages: list[BaseMessage]
    datasets: list[DatasetAttachment]
    embed_language: Language

    @classmethod
    def of(
        cls, store: Store, embed: Embed, request: str, chat_language: Language, embed_origin: str
    ) -> "_Request":
        attachments = store.attachments_of(embed.id)
        datasets = [
            DatasetAttachment(a.id, a.name, ParsedDataset.from_bytes(a.content))
            for a in attachments
            if a.kind == "dataset"
        ]
        images = [
            ImageForModel(a.name, image_url(embed_origin, embed.id, a.id), a.media_type, a.content)
            for a in attachments
            if a.kind == "image"
        ][-MAX_IMAGES_FOR_MODEL:]
        system = base_guide(embed_origin, chat_language, embed.embed_language)
        conversation = store.messages_of(embed.id)
        latest = store.latest_version(embed.id)
        messages = turn_context(system, conversation, latest, request, datasets, images)
        return cls(messages, datasets, embed.embed_language)


@dataclass
class _Reply:
    """What the model answered, filled in by `_model_reply` as it streams."""

    text: str = ""
    html: str | None = None  # The finished document, with datasets and language applied.
    guides: list[str] = field(default_factory=list)  # Kept, so the chat shows them after a reload.
    error: str | None = None  # The reply broke the contract or the model failed: no html.


async def _model_reply(
    model: BaseChatModel, request: _Request, reply: _Reply
) -> AsyncIterator[ChatEvent]:
    """Stream the reply's events into the chat while filling in `reply`. Stores nothing."""
    stream = ReplyStream()
    try:
        async for event in _stream_reply(model, request.messages, stream):
            if event[0] == "guide" and isinstance(event[1], dict):
                reply.guides.append(str(event[1]["name"]))
            yield event
        parsed = parse_reply(stream.raw)
        if parsed.html:
            # The figures go in here, from the file: never through the model (ADR 0002).
            injected = inject_datasets(parsed.html, request.datasets)
            reply.html = with_document_language(injected, request.embed_language)
        reply.text = parsed.text
    except ReplyError as exc:
        # Keep whatever the model said before the broken HTML, so the chat still reads well.
        reply.error, reply.text = str(exc), prose_before_html(stream.raw).strip() or str(exc)
    except Exception as exc:  # The provider failed: bad key, rate limit, network, ...
        reply.error, reply.text = f"The model could not answer: {exc}", MODEL_UNAVAILABLE


def _ending(reply: _Reply, version: Version | None) -> list[ChatEvent]:
    events: list[ChatEvent] = []
    if version:
        events.append(("version", version))
    if reply.error:
        events.append(("error", {"message": reply.error}))
    events.append(("done", {"text": reply.text}))
    return events


async def _stream_reply(
    model: BaseChatModel, messages: list[BaseMessage], stream: ReplyStream
) -> AsyncIterator[ChatEvent]:
    """Stream rounds until the model answers instead of asking for guides."""
    with_guides = model.bind_tools([LOAD_GUIDE_TOOL])
    last_sent_at = 0.0
    last_sent: str | None = None

    for _ in range(MAX_GUIDE_ROUNDS + 1):
        gathered: AIMessageChunk | None = None
        async for chunk in with_guides.astream(messages):
            assert isinstance(chunk, AIMessageChunk)
            gathered = chunk if gathered is None else gathered + chunk
            if text := stream.feed(chunk.text):
                yield "text", {"delta": text}
            progress = stream.work_in_progress()
            now = time.monotonic()
            if progress and progress != last_sent and now - last_sent_at >= PROGRESS_INTERVAL_SECONDS:
                yield "progress", {"html": progress}
                last_sent, last_sent_at = progress, now

        if gathered is None or not gathered.tool_calls:
            return
        messages.append(AIMessage(content=gathered.text, tool_calls=gathered.tool_calls))
        for call in gathered.tool_calls:
            name = call["args"].get("name")
            yield "guide", {"name": name}
            messages.append(ToolMessage(content=load_guide(name), tool_call_id=call["id"] or ""))

    raise ReplyError("The model kept looking up guides without answering.")
