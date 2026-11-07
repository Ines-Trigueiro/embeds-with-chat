"""Multi-round editing: what the model sees each turn, and continuing later."""

from fastapi.testclient import TestClient
from langchain_core.messages import HumanMessage, SystemMessage

from conftest import FakeChatModel, as_journalist, chat, doc, new_embed, only
from embeds.config import Settings
from embeds.editor import create_editor_app


def test_each_turn_sees_the_conversation_text_but_only_the_latest_versions_html(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    fake_model.replies += [
        f"Første utgave.\n```html\n{doc('FIRST-VERSION')}\n```",
        f"Større knapper.\n```html\n{doc('SECOND-VERSION')}\n```",
        f"Tall fra 2025.\n```html\n{doc('THIRD-VERSION')}\n```",
    ]
    embed_id = new_embed(editor)
    chat(editor, embed_id, "Lag en kalkulator")
    chat(editor, embed_id, "Gjør knappene større")

    chat(editor, embed_id, "Bruk tall fra 2025")

    third_prompt = fake_model.received[2]
    assert isinstance(third_prompt[0], SystemMessage)
    conversation = [(type(m).__name__, m.text) for m in third_prompt[1:-1]]
    assert conversation == [
        ("HumanMessage", "Lag en kalkulator"),
        ("AIMessage", "Første utgave."),
        ("HumanMessage", "Gjør knappene større"),
        ("AIMessage", "Større knapper."),
    ]
    request = third_prompt[-1]
    assert isinstance(request, HumanMessage)
    assert "Bruk tall fra 2025" in request.text
    assert "SECOND-VERSION" in request.text
    everything = " ".join(m.text for m in third_prompt)
    assert "FIRST-VERSION" not in everything


def test_the_first_turn_has_no_current_version(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    fake_model.replies.append("Hva slags quiz?")
    chat(editor, new_embed(editor), "Lag en quiz")

    [system, request] = fake_model.received[0]
    assert request.text.strip().endswith("Lag en quiz")
    assert "```html" not in request.text


def test_conversation_and_versions_survive_a_restart(
    settings: Settings, fake_model: FakeChatModel
) -> None:
    fake_model.replies += [f"En.\n```html\n{doc('1')}\n```", f"To.\n```html\n{doc('2')}\n```"]
    with TestClient(create_editor_app(settings, chat_model=fake_model)) as first:
        embed_id = new_embed(first)
        chat(first, embed_id, "Lag noe")
        chat(first, embed_id, "Endre det")

    with TestClient(create_editor_app(settings, chat_model=fake_model)) as second:
        opened = second.get(f"/api/embeds/{embed_id}", headers=as_journalist("kari")).json()

    assert [m["text"] for m in opened["messages"]] == ["Lag noe", "En.", "Endre det", "To."]
    assert [v["number"] for v in opened["versions"]] == [1, 2]
    assert opened["latest_version"]["number"] == 2


def test_every_version_in_the_history_can_be_previewed(
    editor: TestClient, embed_origin: TestClient, fake_model: FakeChatModel
) -> None:
    fake_model.replies += [f"```html\n{doc('ONE')}\n```", f"```html\n{doc('TWO')}\n```"]
    embed_id = new_embed(editor)
    chat(editor, embed_id, "Lag noe")
    chat(editor, embed_id, "Endre det")

    versions = editor.get(f"/api/embeds/{embed_id}", headers=as_journalist("kari")).json()["versions"]

    bodies = [embed_origin.get(v["preview_url"].removeprefix("http://embeds.test")).text for v in versions]
    assert ["ONE" in bodies[0], "TWO" in bodies[1]] == [True, True]


def test_a_failed_turn_does_not_break_the_next_one(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    fake_model.replies += [RuntimeError("overloaded"), f"```html\n{doc('ok')}\n```"]
    embed_id = new_embed(editor)
    chat(editor, embed_id, "Lag noe")

    events = chat(editor, embed_id, "Prøv igjen")

    assert only(events, "version")[0]["number"] == 1
    roles = [type(m).__name__ for m in fake_model.received[1][1:]]
    assert roles == ["HumanMessage", "AIMessage", "HumanMessage"]
