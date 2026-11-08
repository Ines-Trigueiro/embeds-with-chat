"""Shared fixtures: both origins under test, with the chat model swapped for a fake.

The fake chat model is the only internal swap in the suite; everything else is
exercised through the HTTP interface of the two apps.
"""

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable, Sequence
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.messages.tool import tool_call_chunk
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

from embeds.config import Settings
from embeds.editor import create_editor_app
from embeds.embed_origin import create_embed_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path,
        app_origin="http://app.test",
        embed_origin="http://embeds.test",
        _env_file=None,  # type: ignore[call-arg]  # never read a developer's .env in tests
    )


@dataclass(frozen=True)
class FailsMidStream:
    """A scripted reply that streams `text`, then fails the way a dropped provider does."""

    text: str
    error: Exception


class FakeChatModel(BaseChatModel):
    """Replies with scripted text, streamed in tiny chunks, and records every prompt.

    Three-character chunks make sure code fences get split across chunk boundaries,
    the way a real model's tokens split them.
    """

    replies: list[str | AIMessage | Exception | FailsMidStream] = []
    received: list[list[BaseMessage]] = []
    bound_tools: list[Any] = []
    chunk_size: int = 3

    @property
    def _llm_type(self) -> str:
        return "fake"

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | Callable[..., Any] | BaseTool],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> Runnable[LanguageModelInput, AIMessage]:
        self.bound_tools = list(tools)
        return self

    def _next_reply(self, messages: list[BaseMessage]) -> str | AIMessage | FailsMidStream:
        self.received.append(list(messages))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        reply = self._next_reply(messages)
        assert not isinstance(reply, FailsMidStream), "only a streamed reply can fail mid-stream"
        message = reply if isinstance(reply, AIMessage) else AIMessage(content=reply)
        return ChatResult(generations=[ChatGeneration(message=message)])

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        reply = self._next_reply(messages)
        if isinstance(reply, AIMessage):  # A tool call: one chunk, like a real model's final delta.
            tool_call_chunks = [
                tool_call_chunk(name=c["name"], args=json.dumps(c["args"]), id=c["id"], index=i)
                for i, c in enumerate(reply.tool_calls)
            ]
            yield ChatGenerationChunk(
                message=AIMessageChunk(content=reply.text, tool_call_chunks=tool_call_chunks)
            )
            return
        text = reply.text if isinstance(reply, FailsMidStream) else reply
        for start in range(0, len(text), self.chunk_size):
            chunk = text[start : start + self.chunk_size]
            yield ChatGenerationChunk(message=AIMessageChunk(content=chunk))
        if isinstance(reply, FailsMidStream):
            raise reply.error


@pytest.fixture
def fake_model() -> FakeChatModel:
    """Tests script replies with `fake_model.replies.append(...)`."""
    return FakeChatModel(replies=[], received=[])


@pytest.fixture
def editor(settings: Settings, fake_model: FakeChatModel) -> Iterator[TestClient]:
    with TestClient(create_editor_app(settings, chat_model=fake_model)) as client:
        yield client


@pytest.fixture
def embed_origin(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_embed_app(settings)) as client:
        yield client


def load_guide(name: str, call_id: str = "call-1") -> AIMessage:
    """A scripted model reply that asks for a guide."""
    return AIMessage(
        content="", tool_calls=[{"name": "load_guide", "args": {"name": name}, "id": call_id}]
    )


def as_journalist(name: str) -> dict[str, str]:
    return {"X-Journalist": name}


def new_embed(editor: TestClient, journalist: str = "kari", title: str = "Test") -> str:
    response = editor.post("/api/embeds", json={"title": title}, headers=as_journalist(journalist))
    assert response.status_code == 201
    embed_id: str = response.json()["id"]
    return embed_id


def chat(
    editor: TestClient,
    embed_id: str,
    content: str,
    journalist: str = "kari",
    language: str = "nb",
) -> list[tuple[str, Any]]:
    """Send a chat message and return the streamed server-sent events as (event, data)."""
    return streamed(
        editor, f"/api/embeds/{embed_id}/messages", {"content": content, "language": language}, journalist
    )


def translate(
    editor: TestClient, embed_id: str, embed_language: str, journalist: str = "kari", language: str = "nb"
) -> list[tuple[str, Any]]:
    """Ask for a Translation of the current version and return its streamed events."""
    return streamed(
        editor,
        f"/api/embeds/{embed_id}/translations",
        {"embed_language": embed_language, "language": language},
        journalist,
    )


def streamed(
    editor: TestClient, path: str, body: dict[str, str], journalist: str
) -> list[tuple[str, Any]]:
    events: list[tuple[str, Any]] = []
    with editor.stream("POST", path, json=body, headers=as_journalist(journalist)) as response:
        assert response.status_code == 200, response.read()
        assert response.headers["content-type"].startswith("text/event-stream")
        event = "message"
        for line in response.iter_lines():
            if line.startswith("event: "):
                event = line.removeprefix("event: ")
            elif line.startswith("data: "):
                events.append((event, json.loads(line.removeprefix("data: "))))
                event = "message"
    return events


def only(events: list[tuple[str, Any]], name: str) -> list[Any]:
    return [data for event, data in events if event == name]


def doc(body: str) -> str:
    """A minimal complete HTML document that passes the quality check."""
    return (
        '<!doctype html>\n<html lang="nb">\n<head><title>t</title>'
        '<meta name="viewport" content="width=device-width, initial-scale=1"></head>\n'
        f"<body>{body}<p>Kilde: test</p></body>\n</html>"
    )
