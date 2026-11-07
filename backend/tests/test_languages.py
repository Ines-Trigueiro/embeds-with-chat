"""Languages: the journalist's chat language, and each embed's own Embed language."""

import sqlite3

from fastapi.testclient import TestClient

from conftest import FakeChatModel, as_journalist, chat, doc, new_embed
from embeds.config import Settings
from embeds.editor import create_editor_app


def served_html(editor: TestClient, embed_origin: TestClient, embed_id: str) -> str:
    opened = editor.get(f"/api/embeds/{embed_id}", headers=as_journalist("kari")).json()
    url: str = opened["latest_version"]["preview_url"]
    return embed_origin.get(url.removeprefix("http://embeds.test")).text


def test_embed_language_defaults_to_nb_and_can_be_chosen_at_creation(editor: TestClient) -> None:
    default = editor.post("/api/embeds", json={"title": "a"}, headers=as_journalist("kari")).json()
    danish = editor.post(
        "/api/embeds", json={"title": "b", "embed_language": "da"}, headers=as_journalist("kari")
    ).json()

    assert default["embed_language"] == "nb"
    assert danish["embed_language"] == "da"


def test_the_journalist_can_change_an_embeds_language(editor: TestClient) -> None:
    embed_id = new_embed(editor)

    changed = editor.patch(
        f"/api/embeds/{embed_id}", json={"embed_language": "en"}, headers=as_journalist("kari")
    )

    assert changed.status_code == 200
    opened = editor.get(f"/api/embeds/{embed_id}", headers=as_journalist("kari")).json()
    assert opened["embed_language"] == "en"
    other = editor.patch(
        f"/api/embeds/{embed_id}", json={"embed_language": "da"}, headers=as_journalist("ola")
    )
    assert other.status_code == 404


def test_unsupported_languages_are_rejected(editor: TestClient) -> None:
    embed_id = new_embed(editor)

    assert editor.patch(
        f"/api/embeds/{embed_id}", json={"embed_language": "sv"}, headers=as_journalist("kari")
    ).status_code == 422
    assert editor.post(
        f"/api/embeds/{embed_id}/messages",
        json={"content": "hei", "language": "sv"},
        headers=as_journalist("kari"),
    ).status_code == 422


def test_chat_language_and_embed_language_both_reach_the_prompt(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    fake_model.replies.append("What should it show?")
    embed_id = editor.post(
        "/api/embeds", json={"title": "t", "embed_language": "da"}, headers=as_journalist("kari")
    ).json()["id"]

    chat(editor, embed_id, "Make a quiz", language="en")

    system = fake_model.received[0][0].text
    assert "Reply to the journalist in English" in system
    assert "reader-facing text in Danish" in system
    assert 'lang="da"' in system


def test_versions_get_the_embed_language_whatever_the_model_wrote(
    editor: TestClient, embed_origin: TestClient, fake_model: FakeChatModel
) -> None:
    wrong_lang = doc("<p>hej</p>").replace('lang="nb"', 'lang="sv"')
    no_lang = "<!doctype html><HTML><head></head><body>hej</body></HTML>"
    fake_model.replies += [f"```html\n{wrong_lang}\n```", f"```html\n{no_lang}\n```"]
    embed_id = editor.post(
        "/api/embeds", json={"title": "t", "embed_language": "da"}, headers=as_journalist("kari")
    ).json()["id"]

    chat(editor, embed_id, "Lag noe")
    first = served_html(editor, embed_origin, embed_id)
    chat(editor, embed_id, "Endre")
    second = served_html(editor, embed_origin, embed_id)

    assert '<html lang="da">' in first and 'lang="sv"' not in first
    assert '<HTML lang="da">' in second


def test_databases_from_before_embed_languages_are_migrated(
    settings: Settings, fake_model: FakeChatModel
) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(settings.database_path) as db:
        db.execute(
            "CREATE TABLE embeds (id TEXT PRIMARY KEY, journalist TEXT NOT NULL,"
            " title TEXT NOT NULL, created_at TEXT NOT NULL)"
        )
        db.execute("INSERT INTO embeds VALUES ('old-embed-id', 'kari', 'Gammel', '2026-01-01')")

    with TestClient(create_editor_app(settings, chat_model=fake_model)) as editor:
        [old] = editor.get("/api/embeds", headers=as_journalist("kari")).json()

    assert old["title"] == "Gammel"
    assert old["embed_language"] == "nb"
