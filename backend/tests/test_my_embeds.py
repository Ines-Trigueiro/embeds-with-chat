from urllib.parse import quote

from fastapi.testclient import TestClient

from conftest import FakeChatModel, as_journalist, chat
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


def test_creating_an_embed_returns_it_opened(editor: TestClient) -> None:
    created = editor.post("/api/embeds", json={"title": "Valgquiz"}, headers=as_journalist("kari"))

    opened = editor.get(f"/api/embeds/{created.json()['id']}", headers=as_journalist("kari"))
    assert created.status_code == 201
    assert created.json() == opened.json()
    assert created.json()["messages"] == []
    assert created.json()["versions"] == []
    assert created.json()["progress_frame_url"].endswith("/progress-frame")


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
    settings: Settings, fake_model: FakeChatModel
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


# Titles: suggested from the journalist's first message, editable, never overwritten.


def test_an_embed_can_be_created_without_a_title(editor: TestClient) -> None:
    created = editor.post("/api/embeds", json={}, headers=as_journalist("kari"))

    assert created.status_code == 201
    assert created.json()["title"] is None


def untitled_embed(editor: TestClient) -> str:
    embed_id: str = editor.post("/api/embeds", json={}, headers=as_journalist("kari")).json()["id"]
    return embed_id


def listed_titles(editor: TestClient) -> list[str | None]:
    return [e["title"] for e in editor.get("/api/embeds", headers=as_journalist("kari")).json()]


def test_the_first_message_suggests_a_title_before_the_reply(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    fake_model.replies += ['"Quiz: norske fjell"', "How many questions?"]
    embed_id = untitled_embed(editor)

    events = chat(editor, embed_id, "Lag en quiz om norske fjell")

    assert events[0] == ("title", {"title": "Quiz: norske fjell"})
    assert listed_titles(editor) == ["Quiz: norske fjell"]
    assert "Lag en quiz om norske fjell" in fake_model.received[0][-1].text


def test_the_title_falls_back_to_the_start_of_the_message_when_no_suggestion_comes(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    fake_model.replies += [RuntimeError("rate limited"), "How many questions?"]
    embed_id = untitled_embed(editor)
    message = "Lag en quiz om norske fjell med ti spørsmål, bilder og en poengtavle til slutt"

    events = chat(editor, embed_id, message)

    (title,) = [data["title"] for event, data in events if event == "title"]
    assert title == "Lag en quiz om norske fjell med ti spørsmål, bilder og en…"
    assert listed_titles(editor) == [title]


def test_a_title_is_suggested_only_once(editor: TestClient, fake_model: FakeChatModel) -> None:
    fake_model.replies += ["Valgquiz", "Done.", "Done again."]
    embed_id = untitled_embed(editor)
    chat(editor, embed_id, "Lag en valgquiz")

    events = chat(editor, embed_id, "Gjør knappene større")

    assert [e for e, _ in events if e == "title"] == []
    assert len(fake_model.received) == 3  # title, first reply, second reply: no new suggestion
    assert listed_titles(editor) == ["Valgquiz"]


def test_an_embed_created_with_a_title_gets_no_suggestion(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    fake_model.replies.append("Done.")
    embed_id = editor.post(
        "/api/embeds", json={"title": "Strømpris"}, headers=as_journalist("kari")
    ).json()["id"]

    events = chat(editor, embed_id, "Lag en kalkulator")

    assert [e for e, _ in events if e == "title"] == []
    assert listed_titles(editor) == ["Strømpris"]


def test_the_journalist_can_rename_an_embed(editor: TestClient, fake_model: FakeChatModel) -> None:
    fake_model.replies += ["Valgquiz", "Done.", "Done again."]
    embed_id = untitled_embed(editor)
    chat(editor, embed_id, "Lag en valgquiz")

    renamed = editor.patch(
        f"/api/embeds/{embed_id}", json={"title": "  Stortingsvalget 2029  "}, headers=as_journalist("kari")
    )
    chat(editor, embed_id, "Gjør knappene større")

    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Stortingsvalget 2029"
    assert listed_titles(editor) == ["Stortingsvalget 2029"]


def test_renaming_rejects_empty_and_overlong_titles_and_other_journalists(editor: TestClient) -> None:
    embed_id = untitled_embed(editor)

    def rename(title: str, journalist: str = "kari") -> int:
        response = editor.patch(
            f"/api/embeds/{embed_id}", json={"title": title}, headers=as_journalist(journalist)
        )
        return response.status_code

    assert rename("   ") == 422
    assert rename("x" * 201) == 422
    assert rename("Mine", journalist="ola") == 404
    assert listed_titles(editor) == [None]
