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


def translation_request(language: Language) -> str:
    """What the model is asked for a Translation (ADR 0004): the journalist types nothing."""
    name = LANGUAGE_NAMES[language]
    return (
        f"Translate the current version of the embed into {name}. Rewrite all reader-facing "
        f"text (headings, labels, buttons, explanations, alt text and the source line) into "
        f"{name}, and format numbers and dates the way readers of {name} expect. Change "
        "nothing else: keep the layout, the behaviour and the code, and keep every dataset "
        "element exactly as it is, because the data itself is never translated. Reply with "
        "one short sentence about the translation, followed by the whole document."
    )
