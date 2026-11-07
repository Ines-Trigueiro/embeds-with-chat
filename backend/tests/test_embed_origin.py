"""The embed origin: what it serves, and the protections it serves it with (ADR 0001)."""

import re
from urllib.parse import urlsplit

from fastapi.testclient import TestClient

from conftest import FakeChatModel, chat, doc, new_embed, only
from embeds.allowlist import LIBRARIES, MAP_TILE_HOST
from embeds.config import Settings
from embeds.editor import create_editor_app
from embeds.embed_origin import create_embed_app


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


def test_the_system_prompt_names_every_source_the_csp_allows(
    editor: TestClient, embed_origin: TestClient, fake_model: FakeChatModel
) -> None:
    csp = directives(embed_origin.get(make_version(editor, fake_model)).headers["content-security-policy"])
    system = fake_model.received[0][0].text

    for directive in ("script-src", "style-src", "img-src", "font-src"):
        for source in csp[directive]:
            if not source.startswith("'"):  # keywords like 'unsafe-inline' aren't sources
                assert source in system, f"{directive} allows {source}, but the prompt never says so"
    for library in LIBRARIES:
        for url in library.urls():
            assert url in system


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


def test_progress_frame_renders_under_the_same_csp_and_only_trusts_the_editor_origin(
    embed_origin: TestClient,
) -> None:
    response = embed_origin.get("/progress-frame")

    assert response.status_code == 200
    csp = directives(response.headers["content-security-policy"])
    assert csp["connect-src"] == ["'none'"]
    assert '"http://app.test"' in response.text  # the only origin whose drafts it accepts
    assert 'sandbox="allow-scripts"' in response.text


def test_every_embed_origin_response_is_sandboxed_even_when_opened_directly(
    editor: TestClient, embed_origin: TestClient, fake_model: FakeChatModel
) -> None:
    # Opened top-level, outside an <iframe sandbox>, the CSP still forces an opaque origin.
    for path in (make_version(editor, fake_model), "/progress-frame"):
        csp = directives(embed_origin.get(path).headers["content-security-policy"])
        assert csp["sandbox"] == ["allow-scripts"], path


def test_preview_urls_expire(settings: Settings, fake_model: FakeChatModel) -> None:
    expired = settings.model_copy(update={"preview_ttl_seconds": -1})
    with (
        TestClient(create_editor_app(expired, chat_model=fake_model)) as editor,
        TestClient(create_embed_app(expired)) as embed_origin,
    ):
        assert embed_origin.get(make_version(editor, fake_model)).status_code == 404


def test_tampering_with_the_expiry_invalidates_the_preview_url(
    editor: TestClient, embed_origin: TestClient, fake_model: FakeChatModel
) -> None:
    path = make_version(editor, fake_model)
    later = re.sub(r"exp=\d+", "exp=99999999999", path)

    assert later != path
    assert embed_origin.get(later).status_code == 404
