"""The quality check as a gate: findings come with every Version, and publishing respects them."""

from fastapi.testclient import TestClient

from conftest import FakeChatModel, as_journalist, chat, doc, new_embed, only

KARI = as_journalist("kari")
WARNS_ONLY = doc('<img src="data:image/png;base64,AA">')  # no alt text
BLOCKED = doc('<script src="https://evil.example/x.js"></script>')


def version_from(editor: TestClient, fake_model: FakeChatModel, html: str) -> tuple[str, dict]:  # type: ignore[type-arg]
    fake_model.replies.append(f"```html\n{html}\n```")
    embed_id = new_embed(editor)
    [version] = only(chat(editor, embed_id, "Lag noe"), "version")
    return embed_id, version


def test_every_new_version_comes_with_its_findings(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    embed_id, version = version_from(editor, fake_model, BLOCKED)

    assert version["findings"] == [
        {"rule": "external_resource", "severity": "block", "detail": "https://evil.example/x.js"}
    ]
    opened = editor.get(f"/api/embeds/{embed_id}", headers=KARI).json()
    assert opened["versions"][0]["findings"] == version["findings"]


def test_a_version_with_blocking_findings_cannot_be_published(
    editor: TestClient, embed_origin: TestClient, fake_model: FakeChatModel
) -> None:
    embed_id, _ = version_from(editor, fake_model, BLOCKED)

    refused = editor.post(f"/api/embeds/{embed_id}/versions/1/publish?accept_warnings=true", headers=KARI)

    assert refused.status_code == 422
    assert refused.json()["detail"]["findings"][0]["rule"] == "external_resource"
    assert embed_origin.get(f"/e/{embed_id}").status_code == 404


def test_warnings_need_an_explicit_publish_anyway(
    editor: TestClient, embed_origin: TestClient, fake_model: FakeChatModel
) -> None:
    embed_id, _ = version_from(editor, fake_model, WARNS_ONLY)

    unconfirmed = editor.post(f"/api/embeds/{embed_id}/versions/1/publish", headers=KARI)
    assert unconfirmed.status_code == 409
    assert unconfirmed.json()["detail"]["findings"][0]["rule"] == "missing_alt"
    assert embed_origin.get(f"/e/{embed_id}").status_code == 404

    confirmed = editor.post(f"/api/embeds/{embed_id}/versions/1/publish?accept_warnings=true", headers=KARI)
    assert confirmed.status_code == 200
    assert embed_origin.get(f"/e/{embed_id}").status_code == 200


def test_a_clean_version_publishes_straight_away(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    embed_id, version = version_from(editor, fake_model, doc("<p>Ren</p>"))

    assert version["findings"] == []
    assert editor.post(f"/api/embeds/{embed_id}/versions/1/publish", headers=KARI).status_code == 200
