"""Turn recording: each kind of turn's rules, and what it leaves behind.

A turn streams its events while the model answers, records nothing until the stream ends,
then records the finished turn in one store transaction: all of it or nothing.

Events, in order:
- `title`    {"title"}        the embed's suggested Title (first message of an untitled embed only)
- `guide`    {"name"}         the model is reading a guide (zero or more)
- `text`     {"delta"}        prose for the chat, as it arrives
- `progress` {"html"}         the work in progress, at most about once a second
- `version`  Version          a new Version was created from the finished reply
- `error`    {"message"}      the reply broke the contract or the model failed; no Version
- `done`     {"text"}         the final chat text of the model's message
"""

from collections.abc import AsyncIterator
from dataclasses import replace

from langchain_core.language_models import BaseChatModel

from embeds.chat import ChatEvent, Reply, Request, model_reply
from embeds.context import turn_context
from embeds.datasets import DatasetAttachment, ParsedDataset
from embeds.guides import base_guide
from embeds.images import MAX_IMAGES_FOR_MODEL, ImageForModel, image_url
from embeds.languages import Language, translation_request
from embeds.store import Embed, Store, TurnRecord, Version
from embeds.titles import suggest_title

NO_TRANSLATION = "The model replied without a translated version. Please try again."


class TurnRefused(Exception):
    """The turn can't start; nothing was streamed or recorded. The message says why."""


async def journalist_message(
    store: Store,
    model: BaseChatModel,
    embed: Embed,
    content: str,
    chat_language: Language,
    embed_origin: str,
) -> AsyncIterator[ChatEvent]:
    """The journalist's message and the model's reply to it. Both are recorded, even when
    the reply failed, so the journalist sees the error on the turn after a reload."""
    title = None
    if embed.title is None:
        # Before the reply, so the sidebar can name the embed while the journalist waits.
        title = await suggest_title(model, content)
        yield "title", {"title": title}
    request = _request(store, embed, content, chat_language, embed_origin)
    reply = Reply()
    async for event in model_reply(model, request, reply):
        yield event
    version = store.record_turn(
        embed.id,
        TurnRecord(
            request=content,
            kind="message",
            reply=reply.text,
            guides=tuple(reply.guides),
            html=reply.html,
            title=title,
        ),
    )
    for event in _ending(reply, version):
        yield event


def translation(
    store: Store,
    model: BaseChatModel,
    embed: Embed,
    language: Language,
    chat_language: Language,
    embed_origin: str,
) -> AsyncIterator[ChatEvent]:
    """A Translation (ADR 0004): the journalist typed nothing; the current version is
    rewritten into `language`. Refused unless there is a version and the language is new."""
    if store.latest_version(embed.id) is None:
        raise TurnRefused("There is no version to translate yet.")
    if language == embed.embed_language:
        raise TurnRefused("The embed is already in that language.")
    return _translation(store, model, embed, language, chat_language, embed_origin)


async def _translation(
    store: Store,
    model: BaseChatModel,
    embed: Embed,
    language: Language,
    chat_language: Language,
    embed_origin: str,
) -> AsyncIterator[ChatEvent]:
    """Only one that produced a version is recorded: the marker, the new embed language,
    the Version and the reply. A failed one leaves no trace."""
    embed = replace(embed, embed_language=language)
    request = _request(store, embed, translation_request(language), chat_language, embed_origin)
    reply = Reply()
    async for event in model_reply(model, request, reply):
        yield event
    version = None
    if reply.html is None:
        reply.error = reply.error or NO_TRANSLATION
        reply.text = reply.text or NO_TRANSLATION
    else:
        record = TurnRecord(
            request=language,
            kind="translation",
            reply=reply.text,
            guides=tuple(reply.guides),
            html=reply.html,
            embed_language=language,
        )
        version = store.record_turn(embed.id, record)
    for event in _ending(reply, version):
        yield event


def _request(
    store: Store, embed: Embed, request: str, chat_language: Language, embed_origin: str
) -> Request:
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
    return Request(messages, datasets, embed.embed_language)


def _ending(reply: Reply, version: Version | None) -> list[ChatEvent]:
    events: list[ChatEvent] = []
    if version:
        events.append(("version", version))
    if reply.error:
        events.append(("error", {"message": reply.error}))
    events.append(("done", {"text": reply.text}))
    return events
