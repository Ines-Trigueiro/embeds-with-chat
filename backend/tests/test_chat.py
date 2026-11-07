"""The core loop: a chat message in, a streamed reply out, and maybe a Version."""

from urllib.parse import urlsplit

from fastapi.testclient import TestClient

from conftest import FakeChatModel, chat, doc, new_embed, only


def path_of(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.path}?{parts.query}"


def test_reply_with_one_html_block_becomes_a_version_served_by_the_embed_origin(
    editor: TestClient, embed_origin: TestClient, fake_model: FakeChatModel
) -> None:
    html = doc("<h1>Strømpris</h1>")
    fake_model.replies.append(f"Her er kalkulatoren.\n\n```html\n{html}\n```\n")
    embed_id = new_embed(editor)

    events = chat(editor, embed_id, "Lag en strømpriskalkulator")

    [version] = only(events, "version")
    assert version["number"] == 1
    assert version["preview_url"].startswith("http://embeds.test/")
    served = embed_origin.get(path_of(version["preview_url"]))
    assert served.status_code == 200
    # The model's document, as written; the embed origin only adds the resize script.
    assert served.text.startswith(html[: html.index("</body>")])
    assert served.text.rstrip().endswith("</body>\n</html>")
    assert only(events, "error") == []


def test_reply_without_html_is_a_plain_chat_message_and_creates_no_version(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    fake_model.replies.append("Hvilket år skal tallene gjelde for?")
    embed_id = new_embed(editor)

    events = chat(editor, embed_id, "Lag en kalkulator")

    assert only(events, "version") == []
    assert only(events, "error") == []
    assert "".join(e["delta"] for e in only(events, "text")) == "Hvilket år skal tallene gjelde for?"
    assert only(events, "done") == [{"text": "Hvilket år skal tallene gjelde for?"}]


def test_chat_text_never_contains_the_html(editor: TestClient, fake_model: FakeChatModel) -> None:
    fake_model.replies.append(f"Før.\n```html\n{doc('<p>hemmelig</p>')}\n```\nEtter.")
    embed_id = new_embed(editor)

    events = chat(editor, embed_id, "Lag noe")

    streamed = "".join(e["delta"] for e in only(events, "text"))
    assert "hemmelig" not in streamed and "```" not in streamed
    assert only(events, "done")[0]["text"] == "Før.\n\nEtter."


def test_unclosed_html_block_is_an_error_and_creates_no_version(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    fake_model.replies.append("Her:\n```html\n<!doctype html><html><body><p>Avbr")
    embed_id = new_embed(editor)

    events = chat(editor, embed_id, "Lag noe")

    assert only(events, "version") == []
    assert len(only(events, "error")) == 1


def test_several_html_blocks_are_an_error_and_create_no_version(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    fake_model.replies.append(f"```html\n{doc('a')}\n```\nOg en til:\n```html\n{doc('b')}\n```")
    embed_id = new_embed(editor)

    events = chat(editor, embed_id, "Lag noe")

    assert only(events, "version") == []
    assert len(only(events, "error")) == 1


def test_html_fragment_instead_of_a_document_is_an_error(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    fake_model.replies.append("```html\n<div>bare et fragment</div>\n```")
    embed_id = new_embed(editor)

    events = chat(editor, embed_id, "Lag noe")

    assert only(events, "version") == []
    assert len(only(events, "error")) == 1


def test_model_failure_is_reported_as_an_error(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    fake_model.replies.append(RuntimeError("invalid x-api-key"))
    embed_id = new_embed(editor)

    events = chat(editor, embed_id, "Lag noe")

    assert only(events, "version") == []
    [error] = only(events, "error")
    assert "invalid x-api-key" in error["message"]  # the detail, for whoever runs the tool
    assert "x-api-key" not in only(events, "done")[0]["text"]  # the chat stays readable


def test_work_in_progress_is_streamed_while_the_model_writes(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    html = doc("<p>utkast</p>")
    fake_model.replies.append(f"```html\n{html}\n```")
    embed_id = new_embed(editor)

    events = chat(editor, embed_id, "Lag noe")

    progress = only(events, "progress")
    assert progress, "expected at least one progress event"
    assert all(html.startswith(d["html"]) for d in progress)


def test_versions_are_numbered_per_embed(editor: TestClient, fake_model: FakeChatModel) -> None:
    fake_model.replies += [f"```html\n{doc('1')}\n```", f"```html\n{doc('2')}\n```"]
    embed_id = new_embed(editor)

    first = only(chat(editor, embed_id, "Lag noe"), "version")
    second = only(chat(editor, embed_id, "Endre det"), "version")

    assert [v["number"] for v in first + second] == [1, 2]


def test_journalist_cannot_chat_in_someone_elses_embed(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    embed_id = new_embed(editor, journalist="kari")

    response = editor.post(
        f"/api/embeds/{embed_id}/messages", json={"content": "hei"}, headers={"X-Journalist": "ola"}
    )

    assert response.status_code == 404
    assert fake_model.received == []


def test_opening_an_embed_returns_its_messages_and_latest_version(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    fake_model.replies.append(f"Laget.\n```html\n{doc('x')}\n```")
    embed_id = new_embed(editor, title="Valgquiz")
    chat(editor, embed_id, "Lag en quiz")

    opened = editor.get(f"/api/embeds/{embed_id}", headers={"X-Journalist": "kari"}).json()

    assert opened["title"] == "Valgquiz"
    assert [(m["role"], m["text"], m["version_number"]) for m in opened["messages"]] == [
        ("journalist", "Lag en quiz", None),
        ("model", "Laget.", 1),
    ]
    assert opened["latest_version"]["number"] == 1
    assert opened["progress_frame_url"] == "http://embeds.test/progress-frame"
    assert editor.get(f"/api/embeds/{embed_id}", headers={"X-Journalist": "ola"}).status_code == 404
