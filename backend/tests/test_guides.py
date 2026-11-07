"""Guides: best-practice instructions the model loads itself, plus a base guide that always applies."""

from fastapi.testclient import TestClient
from langchain_core.messages import ToolMessage

from conftest import FakeChatModel, chat, doc, load_guide, new_embed, only

GUIDES = ["quiz", "calculator", "chart", "map", "timeline"]


def test_the_model_can_load_a_guide_before_answering(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    fake_model.replies += [load_guide("map"), f"Her er kartet.\n```html\n{doc('kart')}\n```"]
    embed_id = new_embed(editor)

    events = chat(editor, embed_id, "Lag et kart over nye sykkelfelt")

    assert only(events, "guide") == [{"name": "map"}]
    [answer] = [m for m in fake_model.received[1] if isinstance(m, ToolMessage)]
    assert "Leaflet" in answer.text  # the map guide's content reached the model
    assert only(events, "version")[0]["number"] == 1
    assert only(events, "done") == [{"text": "Her er kartet."}]


def test_every_guide_is_offered_to_the_model(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    fake_model.replies.append("Hva vil du lage?")
    chat(editor, new_embed(editor), "Hei")

    [tool] = fake_model.bound_tools
    schema = str(tool)
    assert all(name in schema for name in GUIDES)


def test_an_unknown_guide_is_answered_with_an_error_not_a_crash(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    fake_model.replies += [load_guide("poll"), f"```html\n{doc('x')}\n```"]
    embed_id = new_embed(editor)

    events = chat(editor, embed_id, "Lag en avstemning")

    [answer] = [m for m in fake_model.received[1] if isinstance(m, ToolMessage)]
    assert "no guide called 'poll'" in answer.text.lower()
    assert only(events, "version")[0]["number"] == 1
    assert only(events, "error") == []


def test_the_base_guide_is_always_in_the_system_prompt(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    fake_model.replies.append("Hva vil du lage?")
    chat(editor, new_embed(editor), "Hei")

    system = fake_model.received[0][0].text
    assert "load_guide" in system
    assert "Never invent figures" in system


def test_a_model_that_keeps_loading_guides_is_stopped(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    fake_model.replies += [load_guide("quiz", f"call-{i}") for i in range(10)]
    embed_id = new_embed(editor)

    events = chat(editor, embed_id, "Lag en quiz")

    assert len(only(events, "error")) == 1
    assert only(events, "version") == []
    assert len(fake_model.received) <= 5
