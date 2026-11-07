"""The quality check: one rule per test, each with HTML that passes and HTML that breaks it."""

import pytest

from conftest import doc
from embeds.quality_check import Finding, check

ORIGIN = "http://embeds.test"

GOOD = """<!doctype html>
<html lang="nb">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Strømpris</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
</head>
<body>
<h1>Strømprisen i 2025</h1>
<img src="data:image/png;base64,AAAA" alt="Strømmast">
<img src="http://embeds.test/attachments/abc/logo.png" alt="Logo">
<div id="map"></div>
<p>Kilde: NVE, 1. mars 2025</p>
<script>
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  });
  document.getElementById("map").parentNode.style.margin = "0";
</script>
</body>
</html>"""


def rules(html: str) -> list[tuple[str, str]]:
    return [(f.rule, f.severity) for f in check(html, ORIGIN)]


def test_a_well_behaved_embed_has_no_findings() -> None:
    assert check(GOOD, ORIGIN) == []


@pytest.mark.parametrize(
    "snippet",
    [
        '<script src="https://evil.example/x.js"></script>',
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Inter">',
        '<img src="https://example.com/pic.jpg" alt="x">',
        '<script>fetch("https://api.example.com/track")</script>',
        '<div style="background: url(https://example.com/bg.png)"></div>',
        '<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js"></script>',
        '<script src="//evil.example/x.js"></script>',
    ],
)
def test_network_addresses_outside_the_allowlist_block_publishing(snippet: str) -> None:
    assert ("external_resource", "block") in rules(GOOD.replace("<body>", "<body>" + snippet))


def test_javascript_links_block_publishing() -> None:
    html = GOOD.replace("<body>", '<body><a href="javascript:alert(1)">x</a>')
    assert ("external_resource", "block") in rules(html)


@pytest.mark.parametrize("code", ["document.cookie", "document . cookie", "document['cookie']"])
def test_reading_cookies_blocks_publishing(code: str) -> None:
    html = GOOD.replace("<body>", f"<body><script>const c = {code};</script>")
    assert ("cookie_access", "block") in rules(html)


@pytest.mark.parametrize(
    "code",
    ["window.top.location = 'x'", "parent.document.body", "window.parent.postMessage(1, '*')", "top.location.href", "window.opener"],
)
def test_reaching_for_the_article_page_blocks_publishing(code: str) -> None:
    html = GOOD.replace("<body>", f"<body><script>{code};</script>")
    assert ("page_access", "block") in rules(html)


def test_dom_parent_nodes_are_not_mistaken_for_the_article_page() -> None:
    html = GOOD.replace("<body>", "<body><script>el.parentNode.remove(); node.parent.x = 1;</script>")
    assert ("page_access", "block") not in rules(html)


def test_forms_that_submit_somewhere_block_publishing() -> None:
    html = GOOD.replace("<body>", '<body><form action="/subscribe"><input name="e"></form>')
    assert ("form_submission", "block") in rules(html)
    assert ("form_submission", "block") not in rules(GOOD.replace("<body>", "<body><form><input></form>"))


def test_meta_refresh_blocks_publishing() -> None:
    html = GOOD.replace("<head>", '<head><meta http-equiv="refresh" content="0; url=https://example.com">')
    assert ("redirect", "block") in rules(html)


def test_documents_that_are_too_large_block_publishing() -> None:
    html = GOOD.replace("<body>", "<body><!--" + "x" * 600_000 + "-->")
    assert ("too_large", "block") in rules(html)


def test_images_without_alt_text_are_a_warning() -> None:
    html = GOOD.replace('alt="Strømmast"', "")
    assert ("missing_alt", "warn") in rules(html)


def test_a_missing_source_line_is_a_warning() -> None:
    html = GOOD.replace("<p>Kilde: NVE, 1. mars 2025</p>", "")
    assert ("missing_source", "warn") in rules(html)


@pytest.mark.parametrize("line", ["Kilde: SSB", "Kjelde: SSB", "Source: Eurostat", "Kilde: Danmarks Statistik"])
def test_source_lines_are_recognised_in_every_language(line: str) -> None:
    html = GOOD.replace("Kilde: NVE, 1. mars 2025", line)
    assert ("missing_source", "warn") not in rules(html)


def test_a_missing_viewport_is_a_warning() -> None:
    html = GOOD.replace('<meta name="viewport" content="width=device-width, initial-scale=1">', "")
    assert ("missing_viewport", "warn") in rules(html)


def test_findings_say_what_was_found() -> None:
    html = GOOD.replace("<body>", '<body><script src="https://evil.example/x.js"></script>')
    [finding] = [f for f in check(html, ORIGIN) if f.rule == "external_resource"]
    assert finding == Finding("external_resource", "block", "https://evil.example/x.js")


def test_the_test_suites_minimal_document_is_clean() -> None:
    assert check(doc("<p>hei</p>"), ORIGIN) == []


def test_links_are_their_own_finding() -> None:
    html = GOOD.replace("<p>Kilde: NVE, 1. mars 2025</p>", '<p>Kilde: <a href="https://nve.no">NVE</a></p>')
    assert ("link", "block") in rules(html)
    assert ("external_resource", "block") not in rules(html)
