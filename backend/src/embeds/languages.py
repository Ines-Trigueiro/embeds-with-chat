"""The languages the tool supports: for the journalist's chat, and for each embed's readers."""

import re
from typing import Literal

Language = Literal["nb", "da", "en"]

LANGUAGE_NAMES: dict[Language, str] = {
    "nb": "Norwegian (bokmål)",
    "da": "Danish",
    "en": "English",
}

_HTML_TAG = re.compile(r"<(html)\b([^>]*)>", re.IGNORECASE)
_LANG_ATTRIBUTE = re.compile(r"""\s+lang\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)""", re.IGNORECASE)


def with_document_language(html: str, language: Language) -> str:
    """Set <html lang> to the embed language, replacing whatever the model wrote."""

    def replace(tag: re.Match[str]) -> str:
        attributes = _LANG_ATTRIBUTE.sub("", tag.group(2))
        return f'<{tag.group(1)} lang="{language}"{attributes}>'

    return _HTML_TAG.sub(replace, html, count=1)
