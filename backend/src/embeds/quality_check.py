"""The quality check: what a Version is checked against before it may be published.

A `block` finding stops publishing; a `warn` finding is shown and the journalist may
publish anyway. The CSP and sandbox (ADR 0001) are what actually protect readers; this
check is how the journalist finds out, before readers do, that something won't work or
shouldn't go out. Findings carry a rule code; the UI words them in the journalist's language.
"""

import re
from dataclasses import dataclass
from typing import Literal

from bs4 import BeautifulSoup, Tag

from embeds.allowlist import allowed_url_prefixes

Severity = Literal["block", "warn"]
MAX_BYTES = 500_000

_ABSOLUTE_URL = re.compile(r"""https?://[^\s"'`()<>\\]+""", re.IGNORECASE)
_URL_ATTRIBUTES = ("src", "href", "action", "formaction", "poster", "data", "background", "srcset")
_COOKIE = re.compile(r"""document\s*(\.\s*cookie\b|\[\s*['"]cookie['"]\s*\])""", re.IGNORECASE)
_PAGE_ACCESS = re.compile(
    r"""\b(window|self|globalThis)\s*\.\s*(top|parent|opener)\b"""
    r"""|(?<![\w$.])(top|parent|opener)\s*\.\s*(location|document|postMessage|frames|window)\b"""
)
_SOURCE_LINE = re.compile(r"\b(kilde|kjelde|source)\s*:", re.IGNORECASE)


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: Severity
    detail: str = ""


def check(html: str, embed_origin: str) -> list[Finding]:
    """Check the document as the model wrote it: pass it with dataset markers empty,
    since a dataset's cells are data, not code (ADR 0002; `version_view` does this)."""
    soup = BeautifulSoup(html, "html.parser")
    allowed = allowed_url_prefixes(embed_origin)
    return [
        *_links(soup, allowed),
        *_external_resources(html, soup, allowed),
        *_pattern("cookie_access", _COOKIE, html),
        *_pattern("page_access", _PAGE_ACCESS, html),
        *_form_submissions(soup),
        *_redirects(soup),
        *_size(html),
        *_missing_alt(soup),
        *_missing_viewport(soup),
        *_missing_source(soup),
    ]


def has_blockers(findings: list[Finding]) -> bool:
    return any(f.severity == "block" for f in findings)


def _tags(soup: BeautifulSoup, *names: str) -> list[Tag]:
    return [t for t in soup.find_all(names or True) if isinstance(t, Tag)]


def _external_links(soup: BeautifulSoup, allowed: tuple[str, ...]) -> set[str]:
    hrefs = (str(a.get("href", "")).strip() for a in _tags(soup, "a"))
    return {h for h in hrefs if h.lower().startswith(("http:", "https:")) and not h.startswith(allowed)}


def _links(soup: BeautifulSoup, allowed: tuple[str, ...]) -> list[Finding]:
    """Links can't open anything from inside the sandbox; the source belongs in plain text."""
    return [Finding("link", "block", url) for url in sorted(_external_links(soup, allowed))]


def _external_resources(html: str, soup: BeautifulSoup, allowed: tuple[str, ...]) -> list[Finding]:
    links = _external_links(soup, allowed)  # Reported by `_links` instead.
    found: list[str] = [
        url
        for url in _ABSOLUTE_URL.findall(html)
        if not url.startswith(allowed) and url not in links
    ]
    for tag in _tags(soup):
        for attribute in _URL_ATTRIBUTES:
            value = tag.get(attribute)
            if not isinstance(value, str):
                continue
            value = value.strip()
            if value.startswith("//") or value.lower().startswith("javascript:"):
                found.append(value)
    unique = dict.fromkeys(found)  # Keep the order, drop repeats.
    return [Finding("external_resource", "block", url) for url in unique]


def _pattern(rule: str, pattern: re.Pattern[str], html: str) -> list[Finding]:
    match = pattern.search(html)
    return [Finding(rule, "block", match.group(0))] if match else []


def _form_submissions(soup: BeautifulSoup) -> list[Finding]:
    return [
        Finding("form_submission", "block", str(form.get("action")))
        for form in _tags(soup, "form")
        if form.has_attr("action")
    ]


def _redirects(soup: BeautifulSoup) -> list[Finding]:
    return [
        Finding("redirect", "block", str(meta.get("content", "")))
        for meta in _tags(soup, "meta")
        if str(meta.get("http-equiv", "")).lower() == "refresh"
    ]


def _size(html: str) -> list[Finding]:
    size = len(html.encode())
    return [Finding("too_large", "block", f"{size // 1000} kB")] if size > MAX_BYTES else []


def _missing_alt(soup: BeautifulSoup) -> list[Finding]:
    missing = [img for img in _tags(soup, "img") if not img.has_attr("alt")]
    return [Finding("missing_alt", "warn", str(len(missing)))] if missing else []


def _missing_viewport(soup: BeautifulSoup) -> list[Finding]:
    viewport = [m for m in _tags(soup, "meta") if str(m.get("name", "")).lower() == "viewport"]
    return [] if viewport else [Finding("missing_viewport", "warn")]


def _missing_source(soup: BeautifulSoup) -> list[Finding]:
    for hidden in _tags(soup, "script", "style"):
        hidden.decompose()
    visible = soup.get_text(" ")
    return [] if _SOURCE_LINE.search(visible) else [Finding("missing_source", "warn")]
