from urllib.parse import quote

from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

from conftest import as_journalist
from embeds.config import Settings
from embeds.editor import create_editor_app


def test_journalist_sees_embed_they_created_under_my_embeds(editor: TestClient) -> None:
    created = editor.post(
        "/api/embeds", json={"title": "Strømpriskalkulator"}, headers=as_journalist("kari")
    )
    assert created.status_code == 201

    listed = editor.get("/api/embeds", headers=as_journalist("kari"))

    assert listed.status_code == 200
    assert [e["title"] for e in listed.json()] == ["Strømpriskalkulator"]
    assert listed.json()[0]["id"] == created.json()["id"]


def test_my_embeds_lists_only_the_requesting_journalists_embeds(editor: TestClient) -> None:
    editor.post("/api/embeds", json={"title": "Valgquiz"}, headers=as_journalist("kari"))
    editor.post("/api/embeds", json={"title": "Sykkelkart"}, headers=as_journalist("ola"))

    listed = editor.get("/api/embeds", headers=as_journalist("ola"))

    assert [e["title"] for e in listed.json()] == ["Sykkelkart"]


def test_requests_without_a_journalist_are_rejected(editor: TestClient) -> None:
    assert editor.get("/api/embeds").status_code == 422
    assert editor.post("/api/embeds", json={"title": "x"}).status_code == 422


def test_embed_ids_are_random_not_sequential(editor: TestClient) -> None:
    ids = [
        editor.post("/api/embeds", json={"title": f"e{i}"}, headers=as_journalist("kari")).json()["id"]
        for i in range(3)
    ]

    assert len(set(ids)) == 3
    assert all(len(i) >= 12 and not i.isdigit() for i in ids)


def test_embeds_survive_an_app_restart(
    settings: Settings, fake_model: GenericFakeChatModel
) -> None:
    with TestClient(create_editor_app(settings, chat_model=fake_model)) as first:
        first.post("/api/embeds", json={"title": "Tidslinje"}, headers=as_journalist("kari"))

    with TestClient(create_editor_app(settings, chat_model=fake_model)) as second:
        listed = second.get("/api/embeds", headers=as_journalist("kari"))

    assert [e["title"] for e in listed.json()] == ["Tidslinje"]


def test_journalist_names_outside_latin1_work_when_url_encoded(editor: TestClient) -> None:
    # Browsers refuse non-Latin-1 header values, so the frontend URL-encodes the name.
    lukasz = {"X-Journalist": quote("Łukasz 🗞")}
    editor.post("/api/embeds", json={"title": "Valgquiz"}, headers=lukasz)

    listed = editor.get("/api/embeds", headers=lukasz)

    assert [e["title"] for e in listed.json()] == ["Valgquiz"]


def test_encoded_and_plain_spellings_of_a_name_are_the_same_journalist(editor: TestClient) -> None:
    editor.post("/api/embeds", json={"title": "Sykkelkart"}, headers={"X-Journalist": "%4Fla"})

    listed = editor.get("/api/embeds", headers={"X-Journalist": "Ola"})

    assert [e["title"] for e in listed.json()] == ["Sykkelkart"]


def test_badly_encoded_journalist_names_are_rejected(editor: TestClient) -> None:
    assert editor.get("/api/embeds", headers={"X-Journalist": "%FF"}).status_code == 422
