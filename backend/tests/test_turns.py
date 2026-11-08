"""A turn is recorded entirely or not at all: reopening the embed shows what its events said."""

from fastapi.testclient import TestClient

from conftest import FailsMidStream, FakeChatModel, as_journalist, chat, doc, new_embed, only, opened, translate


def test_a_reply_that_fails_mid_stream_leaves_the_conversation_its_events_implied(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    fake_model.replies += [
        "Strømpris",
        FailsMidStream(f"Her kommer den.\n```html\n{doc('<p>halv')}", RuntimeError("connection reset")),
    ]
    embed_id = editor.post("/api/embeds", json={}, headers=as_journalist("kari")).json()["id"]

    events = chat(editor, embed_id, "Lag en strømpriskalkulator")

    assert [e for e, _ in events][0] == "title"
    assert only(events, "text") and only(events, "error") and not only(events, "version")
    (done,) = only(events, "done")
    embed = opened(editor, embed_id)
    assert embed["title"] == "Strømpris"
    assert [(m["role"], m["text"], m["version_number"]) for m in embed["messages"]] == [
        ("journalist", "Lag en strømpriskalkulator", None),
        ("model", done["text"], None),
    ]
    assert embed["versions"] == [] and embed["latest_version"] is None


def test_a_translation_that_fails_mid_stream_leaves_no_trace(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    fake_model.replies.append(f"Laget.\n```html\n{doc('<p>Hei</p>')}\n```")
    embed_id = new_embed(editor)
    chat(editor, embed_id, "Lag noe")
    before = opened(editor, embed_id)
    fake_model.replies.append(
        FailsMidStream(f"Oversatt.\n```html\n{doc('<p>Hej')}", RuntimeError("connection reset"))
    )

    events = translate(editor, embed_id, "da")

    assert only(events, "text") and only(events, "error") and not only(events, "version")
    after = opened(editor, embed_id)
    assert after["embed_language"] == "nb"
    assert after["messages"] == before["messages"]
    assert after["versions"] == before["versions"]
