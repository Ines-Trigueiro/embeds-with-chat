"""Shared fixtures: both origins under test, with the chat model swapped for a fake.

The fake chat model is the only internal swap in the suite; everything else is
exercised through the HTTP interface of the two apps.
"""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
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


class FakeChatModel(BaseChatModel):
    """Replies with scripted text, streamed in tiny chunks, and records every prompt.

    Three-character chunks make sure code fences get split across chunk boundaries,
    the way a real model's tokens split them.
    """

    replies: list[str | Exception] = []
    received: list[list[BaseMessage]] = []
    chunk_size: int = 3

    @property
    def _llm_type(self) -> str:
        return "fake"

    def _next_reply(self, messages: list[BaseMessage]) -> str:
        self.received.append(messages)
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
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=reply))])

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        reply = self._next_reply(messages)
        for start in range(0, len(reply), self.chunk_size):
            chunk = reply[start : start + self.chunk_size]
            yield ChatGenerationChunk(message=AIMessageChunk(content=chunk))


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


def as_journalist(name: str) -> dict[str, str]:
    return {"X-Journalist": name}


def new_embed(editor: TestClient, journalist: str = "kari", title: str = "Test") -> str:
    response = editor.post("/api/embeds", json={"title": title}, headers=as_journalist(journalist))
    assert response.status_code == 201
    embed_id: str = response.json()["id"]
    return embed_id


def chat(
    editor: TestClient, embed_id: str, content: str, journalist: str = "kari"
) -> list[tuple[str, Any]]:
    """Send a chat message and return the streamed server-sent events as (event, data)."""
    events: list[tuple[str, Any]] = []
    with editor.stream(
        "POST",
        f"/api/embeds/{embed_id}/messages",
        json={"content": content},
        headers=as_journalist(journalist),
    ) as response:
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
    """A minimal complete HTML document, as the model is asked to produce."""
    return f"<!doctype html>\n<html lang=\"nb\">\n<head><title>t</title></head>\n<body>{body}</body>\n</html>"
