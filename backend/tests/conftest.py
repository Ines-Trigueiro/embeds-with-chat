"""Shared fixtures: both origins under test, with the chat model swapped for a fake.

The fake chat model is the only internal swap in the suite; everything else is
exercised through the HTTP interface of the two apps.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

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


@pytest.fixture
def fake_replies() -> list[AIMessage]:
    """Replies the fake model will give, in order. Tests append to this list."""
    return []


@pytest.fixture
def fake_model(fake_replies: list[AIMessage]) -> GenericFakeChatModel:
    return GenericFakeChatModel(messages=iter(fake_replies))


@pytest.fixture
def editor(settings: Settings, fake_model: GenericFakeChatModel) -> Iterator[TestClient]:
    with TestClient(create_editor_app(settings, chat_model=fake_model)) as client:
        yield client


@pytest.fixture
def embeds(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_embed_app(settings)) as client:
        yield client


def as_journalist(name: str) -> dict[str, str]:
    return {"X-Journalist": name}
