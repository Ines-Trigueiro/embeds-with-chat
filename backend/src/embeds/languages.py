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


def language_instructions(chat_language: Language, embed_language: Language) -> str:
    return (
        "## Languages\n\n"
        f"- Reply to the journalist in {LANGUAGE_NAMES[chat_language]}.\n"
        f"- Write all reader-facing text in {LANGUAGE_NAMES[embed_language]} and set "
        f'<html lang="{embed_language}">, whatever language the journalist writes in.\n'
        "- Format numbers and dates the way readers of that language expect.\n"
    )


def with_document_language(html: str, language: Language) -> str:
    """Set <html lang> to the embed language, replacing whatever the model wrote."""

    def replace(tag: re.Match[str]) -> str:
        attributes = _LANG_ATTRIBUTE.sub("", tag.group(2))
        return f'<{tag.group(1)} lang="{language}"{attributes}>'

    return _HTML_TAG.sub(replace, html, count=1)
