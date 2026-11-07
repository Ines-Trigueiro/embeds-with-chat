"""The embed origin: what it serves, and the protections it serves it with (ADR 0001)."""

from urllib.parse import urlsplit

from fastapi.testclient import TestClient

from conftest import FakeChatModel, chat, doc, new_embed, only
from embeds.allowlist import LIBRARIES, MAP_TILE_HOST


def test_embed_origin_returns_404_for_unknown_embeds(embed_origin: TestClient) -> None:
    assert embed_origin.get("/e/does-not-exist").status_code == 404


def make_version(editor: TestClient, fake_model: FakeChatModel) -> str:
    fake_model.replies.append(f"```html\n{doc('<p>hei</p>')}\n```")
    [version] = only(chat(editor, new_embed(editor), "Lag noe"), "version")
    url: str = version["preview_url"]
    parts = urlsplit(url)
    return f"{parts.path}?{parts.query}"


def directives(csp: str) -> dict[str, list[str]]:
    parsed = {}
    for directive in csp.split(";"):
        name, *values = directive.split()
        parsed[name] = values
    return parsed


def test_versions_are_served_with_the_allowlist_csp(
    editor: TestClient, embed_origin: TestClient, fake_model: FakeChatModel
) -> None:
    response = embed_origin.get(make_version(editor, fake_model))

    csp = directives(response.headers["content-security-policy"])
    assert csp["default-src"] == ["'none'"]
    assert csp["connect-src"] == ["'none'"]
    assert csp["form-action"] == ["'none'"]
    assert "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/" in csp["script-src"]
    assert "https://cdnjs.cloudflare.com" not in csp["script-src"], "whole CDN must not be allowed"
    assert MAP_TILE_HOST in csp["img-src"]
    assert "http://embeds.test" in csp["img-src"]


def test_the_system_prompt_lists_every_library_the_csp_allows(
    editor: TestClient, fake_model: FakeChatModel
) -> None:
    make_version(editor, fake_model)

    system = fake_model.received[0][0].text
    for library in LIBRARIES:
        for url in library.urls():
            assert url in system
    assert "tile.openstreetmap.org" in system


def test_preview_without_a_valid_signature_is_not_found(
    editor: TestClient, embed_origin: TestClient, fake_model: FakeChatModel
) -> None:
    path = make_version(editor, fake_model).split("?")[0]

    assert embed_origin.get(path).status_code == 404
    assert embed_origin.get(path + "?sig=" + "0" * 32).status_code == 404


def test_preview_signature_is_bound_to_one_version(
    editor: TestClient, embed_origin: TestClient, fake_model: FakeChatModel
) -> None:
    path, query = make_version(editor, fake_model).split("?")
    fake_model.replies.append(f"```html\n{doc('2')}\n```")
    embed_id = path.split("/")[2]
    chat(editor, embed_id, "Endre")

    other_version = path.rsplit("/", 1)[0] + "/2"
    assert embed_origin.get(f"{other_version}?{query}").status_code == 404


def test_draft_frame_renders_under_the_same_csp_and_only_trusts_the_editor_origin(
    embed_origin: TestClient,
) -> None:
    response = embed_origin.get("/draft-frame")

    assert response.status_code == 200
    csp = directives(response.headers["content-security-policy"])
    assert csp["connect-src"] == ["'none'"]
    assert '"http://app.test"' in response.text  # the only origin whose drafts it accepts
    assert 'sandbox="allow-scripts"' in response.text
