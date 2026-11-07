"""The embed origin: serves embeds, on a separate origin from the editor (ADR 0001)."""

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse

from embeds.allowlist import content_security_policy
from embeds.config import Settings
from embeds.previews import Previews
from embeds.progress_frame import progress_frame_page
from embeds.store import Store


def embed_headers(settings: Settings) -> dict[str, str]:
    return {
        "Content-Security-Policy": content_security_policy(settings.embed_origin),
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Cache-Control": "no-store",
    }


def create_embed_app(settings: Settings) -> FastAPI:
    store = Store(settings.database_path)
    previews = Previews.from_settings(settings)
    progress_page = progress_frame_page(editor_origin=settings.app_origin)
    app = FastAPI(title="Embeds with chat – embed origin", docs_url=None, redoc_url=None)

    @app.get("/preview/{embed_id}/{number}")
    def preview(embed_id: str, number: int, exp: int = 0, sig: str = "") -> Response:
        """Any Version, for the journalist's preview. 404 unless signed and unexpired."""
        valid = previews.is_valid(embed_id, number, exp, sig)
        version = store.version(embed_id, number) if valid else None
        if version is None:
            raise HTTPException(status_code=404)
        return HTMLResponse(version.html, headers=embed_headers(settings))

    @app.get("/progress-frame")
    def progress_frame() -> Response:
        return HTMLResponse(progress_page, headers=embed_headers(settings))

    return app
