"""Guides: best-practice instructions for the model, as markdown files a non-developer can edit.

The base guide is the system prompt. The others are loaded by the model itself through
the `load_guide` tool, for the kind of embed it is building.
"""

from pathlib import Path
from string import Template
from typing import Any, Literal, get_args

from embeds.allowlist import LIBRARIES, MAP_ATTRIBUTION, MAP_TILES
from embeds.languages import LANGUAGE_NAMES, Language

GUIDES_DIR = Path(__file__).parent / "guides"
GuideName = Literal["quiz", "calculator", "chart", "map", "timeline"]
GUIDE_NAMES: tuple[GuideName, ...] = get_args(GuideName)

LOAD_GUIDE_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "load_guide",
        "description": (
            "Load the best-practice guide for one kind of embed. Call it before building "
            "something new, and follow what it says."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "enum": list(GUIDE_NAMES),
                    "description": "The kind of embed.",
                }
            },
            "required": ["name"],
        },
    },
}


def base_guide(embed_origin: str, chat_language: Language, embed_language: Language) -> str:
    """The base guide, with the allowlist (from the same source as the CSP) and languages."""
    libraries = "\n".join(
        f"  - {lib.name}, for {lib.purpose}: " + ", ".join(lib.urls()) for lib in LIBRARIES
    )
    template = Template((GUIDES_DIR / "base.md").read_text())
    return template.substitute(
        guide_names=", ".join(GUIDE_NAMES),
        libraries=libraries,
        map_tiles=MAP_TILES,
        map_attribution=MAP_ATTRIBUTION,
        embed_origin=embed_origin,
        chat_language=LANGUAGE_NAMES[chat_language],
        embed_language=LANGUAGE_NAMES[embed_language],
        embed_language_code=embed_language,
    )


def load_guide(name: object) -> str:
    """The guide's text, or an error the model can read and recover from.

    `name` comes from the model, so it is checked here rather than trusted as a GuideName.
    """
    if name not in GUIDE_NAMES:
        return f"Error: there is no guide called {name!r}. Available guides: {', '.join(GUIDE_NAMES)}."
    return (GUIDES_DIR / f"{name}.md").read_text()
