"""The embed origin: serves embeds to readers, on a separate origin (ADR 0001)."""

from fastapi import FastAPI

from embeds.config import Settings


def create_embed_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="Embeds with chat – embed origin", docs_url=None, redoc_url=None)
    return app
