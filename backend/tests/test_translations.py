"""Translation: changing an embed's language rewrites the current version into it (ADR 0004)."""

from fastapi.testclient import TestClient

from conftest import FakeChatModel, as_journalist, chat, doc, new_embed, only, translate


def embed_with_a_version(editor: TestClient, fake_model: FakeChatModel, body: str = "<p>Hei</p>") -> str:
    fake_model.replies.append(f"Laget.\n```html\n{doc(body)}\n```")
    embed_id = new_embed(editor)
    chat(editor, embed_id, "Lag noe")
    return embed_id


def opened(editor: TestClient, embed_id: str) -> dict:  # type: ignore[type-arg]
    response = editor.get(f"/api/embeds/{embed_id}", headers=as_journalist("kari"))
    return response.json()  # type: ignore[no-any-return]


def test_a_translation_creates_a_new_version_in_the_new_language(
    editor: TestClient, embed_origin: TestClient, fake_model: FakeChatModel
) -> None:
    embed_id = embed_with_a_version(editor, fake_model)
    fake_model.replies.append(f"Translated.\n```html\n{doc('<p>Hej</p>')}\n```")

    events = translate(editor, embed_id, "da")

    (version,) = only(events, "version")
    assert version["number"] == 2
    embed = opened(editor, embed_id)
    assert embed["embed_language"] == "da"
    served = embed_origin.get(version["preview_url"].removeprefix("http://embeds.test")).text
    assert '<html lang="da">' in served
    assert "Hej" in served


def test_a_failed_translation_keeps_the_language_and_creates_no_version(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    embed_id = embed_with_a_version(editor, fake_model)
    fake_model.replies.append(RuntimeError("rate limited"))

    events = translate(editor, embed_id, "da")

    assert only(events, "error") and not only(events, "version")
    embed = opened(editor, embed_id)
    assert embed["embed_language"] == "nb"
    assert len(embed["versions"]) == 1


def test_there_must_be_a_version_and_a_new_language_to_translate(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    def status(embed_id: str, language: str, journalist: str = "kari") -> int:
        response = editor.post(
            f"/api/embeds/{embed_id}/translations",
            json={"embed_language": language},
            headers=as_journalist(journalist),
        )
        return response.status_code

    empty = new_embed(editor)
    with_version = embed_with_a_version(editor, fake_model)

    assert status(empty, "da") == 409
    assert status(with_version, "nb") == 409  # already in that language
    assert status(with_version, "sv") == 422
    assert status(with_version, "da", journalist="ola") == 404
    assert fake_model.received[1:] == []  # no model call for any of them


def test_the_translation_is_in_the_conversation_and_in_the_next_prompt(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    embed_id = embed_with_a_version(editor, fake_model)
    fake_model.replies += [f"Oversat.\n```html\n{doc('<p>Hej</p>')}\n```", "Gjort."]
    translate(editor, embed_id, "da")

    chat(editor, embed_id, "Gjør teksten større")

    messages = opened(editor, embed_id)["messages"]
    assert [(m["role"], m["kind"], m["text"]) for m in messages][2:4] == [
        ("journalist", "translation", "da"),
        ("model", "message", "Oversat."),
    ]
    assert messages[3]["version_number"] == 2
    next_prompt = fake_model.received[-1]
    assert any("Translate the current version of the embed into Danish" in m.text for m in next_prompt[1:-1])
    assert "reader-facing text in Danish" in next_prompt[0].text  # the new embed language
    assert "Hej" in next_prompt[-1].text  # building on the translated version


def test_a_translation_keeps_dataset_values_exactly_as_attached(
    editor: TestClient, embed_origin: TestClient, fake_model: FakeChatModel
) -> None:
    embed_id = new_embed(editor)
    attached = editor.post(
        f"/api/embeds/{embed_id}/attachments",
        files={"file": ("priser.csv", "by,pris\nOslo,1.25\nBergen,0.98\n".encode(), "text/csv")},
        headers=as_journalist("kari"),
    ).json()
    element = f'<script type="application/json" data-dataset="{attached["id"]}"></script>'
    fake_model.replies += [
        f"Laget.\n```html\n{doc(element)}\n```",
        f"Translated.\n```html\n{doc(element + '<p>Prices</p>')}\n```",
    ]
    chat(editor, embed_id, "Vis prisene")

    (version,) = only(translate(editor, embed_id, "en"), "version")

    served = embed_origin.get(version["preview_url"].removeprefix("http://embeds.test")).text
    assert '"by": "Oslo"' in served or '"by":"Oslo"' in served
    assert "1.25" in served and "Bergen" in served
