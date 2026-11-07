"""In a real browser: a published embed can't reach the article page around it (ADR 0001).

Both origins run on 127.0.0.1 and differ only by port. Cookies ignore ports, so this
proves the sandbox itself, not the different host name, keeps the reader's cookies away.
"""

import json
import socket
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import pytest
import uvicorn

from conftest import FakeChatModel, doc
from embeds.config import Settings
from embeds.editor import create_editor_app
from embeds.embed_origin import create_embed_app
from embeds.store import Store

playwright_api = pytest.importorskip("playwright.sync_api")

HOSTILE_EMBED = doc("""
<div id="tall" style="height: 1234px">Tall content</div>
<script>
  const results = {};
  const attempt = (name, fn) => {
    try { results[name] = String(fn()); } catch (e) { results[name] = "blocked: " + e.name; }
  };
  attempt("cookie", () => document.cookie);
  attempt("parentDom", () => window.parent.document.title);
  attempt("topDom", () => window.top.document.body.innerHTML = "HACKED");
  attempt("storage", () => localStorage.getItem("x"));
  attempt("popup", () => window.open("https://example.com/popup"));
  attempt("navigate", () => { window.top.location.href = "https://example.com/phish"; return "attempted"; });
  document.body.dataset.results = JSON.stringify(results);
</script>
""")


@dataclass
class Running:
    editor_url: str
    embed_url: str
    store: Store


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def serve(app: Any, port: int) -> uvicorn.Server:
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    deadline = time.monotonic() + 10
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("server did not start")
        time.sleep(0.05)
    return server


@pytest.fixture
def running(tmp_path: Path) -> Iterator[Running]:
    editor_port, embed_port = free_port(), free_port()
    settings = Settings(
        data_dir=tmp_path,
        app_origin=f"http://127.0.0.1:{editor_port}",
        embed_origin=f"http://127.0.0.1:{embed_port}",
        _env_file=None,  # type: ignore[call-arg]
    )
    model = FakeChatModel(replies=[f"```html\n{HOSTILE_EMBED}\n```"], received=[])
    servers = [
        serve(create_editor_app(settings, chat_model=model), editor_port),
        serve(create_embed_app(settings), embed_port),
    ]
    yield Running(settings.app_origin, settings.embed_origin, Store(settings.database_path))
    for server in servers:
        server.should_exit = True


def publish_hostile_embed(running: Running) -> str:
    """The quality check refuses this embed, so publish it behind the check's back:
    the point is that readers stay safe even if something hostile gets published."""
    headers = {"X-Journalist": "kari"}
    with httpx.Client(base_url=running.editor_url, headers=headers) as client:
        embed_id: str = client.post("/api/embeds", json={"title": "Fiendtlig"}).json()["id"]
        client.post(f"/api/embeds/{embed_id}/messages", json={"content": "lag", "language": "nb"})
        refused = client.post(f"/api/embeds/{embed_id}/versions/1/publish")
        assert refused.status_code == 422, "the quality check should refuse this embed"
    running.store.publish(embed_id, 1)
    return embed_id


@pytest.fixture
def browser() -> Iterator[Any]:
    with playwright_api.sync_playwright() as p:
        try:
            launched = p.chromium.launch()
        except Exception as exc:  # Browser not installed: `uv run playwright install chromium`
            pytest.skip(f"Chromium not available: {exc}")
        yield launched
        launched.close()


def test_a_published_embed_cannot_reach_the_article_page_and_sizes_itself(
    running: Running, browser: Any
) -> None:
    embed_id = publish_hostile_embed(running)
    page = browser.new_page()
    popups: list[Any] = []
    page.on("popup", lambda popup: popups.append(popup))
    article_url = f"{running.editor_url}/test-article?embed={embed_id}"

    page.goto(article_url)
    frame_element = page.wait_for_selector("iframe")
    frame = frame_element.content_frame()
    frame.wait_for_selector("body[data-results]")
    results = json.loads(frame.get_attribute("body", "data-results"))
    page.wait_for_function("document.querySelector('iframe').offsetHeight > 1000")

    # The article page set a cookie; the embed must not be able to read it.
    assert page.evaluate("document.cookie").startswith("reader_session=")
    assert "secret-reader-cookie" not in results["cookie"]
    assert results["cookie"].startswith("blocked")
    # It can't read or change the page around it.
    assert results["parentDom"].startswith("blocked")
    assert results["topDom"].startswith("blocked")
    assert page.inner_text("#after-embed").startswith("Maecenas")
    assert page.title() == "Testartikkel"
    # It can't open popups or send the reader elsewhere.
    assert popups == []
    assert page.url == article_url
    # It is sandboxed, and the iframe follows its content's height.
    assert frame_element.get_attribute("sandbox") == "allow-scripts"
    height = frame_element.evaluate("el => el.offsetHeight")
    assert 1234 <= height <= 1300
