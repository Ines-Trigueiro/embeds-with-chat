"""The embed origin: serves embeds, on a separate origin from the editor (ADR 0001)."""

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse

from embeds.allowlist import content_security_policy
from embeds.config import Settings
from embeds.delivery import loader_js, with_resize_reporting
from embeds.previews import Previews
from embeds.progress_frame import progress_frame_page
from embeds.store import Store, Version


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
    loader = loader_js(settings.embed_origin)
    app = FastAPI(title="Embeds with chat – embed origin", docs_url=None, redoc_url=None)

    def serve(version: Version | None) -> Response:
        if version is None:
            raise HTTPException(status_code=404)
        return HTMLResponse(with_resize_reporting(version.html), headers=embed_headers(settings))

    @app.get("/e/{embed_id}")
    def latest_published(embed_id: str) -> Response:
        """What the Snippet shows by default: the newest published version."""
        return serve(store.version_for_readers(embed_id))

    @app.get("/e/{embed_id}/v/{number}")
    def pinned(embed_id: str, number: int) -> Response:
        """One version, pinned; only if it is published."""
        return serve(store.version_for_readers(embed_id, number))

    @app.get("/attachments/{embed_id}/{attachment_id}")
    def attached_image(embed_id: str, attachment_id: str) -> Response:
        """An image the journalist attached, for embeds to show. Never anything but an image."""
        attachment = store.attachment(embed_id, attachment_id)
        if attachment is None or attachment.kind != "image":
            raise HTTPException(status_code=404)
        return Response(
            attachment.content,
            media_type=attachment.media_type,
            headers={
                "Content-Security-Policy": "default-src 'none'; sandbox",
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "public, max-age=31536000, immutable",
            },
        )

    @app.get("/loader.js")
    def loader_script() -> Response:
        return Response(
            loader,
            media_type="text/javascript; charset=utf-8",
            headers={"Cache-Control": "public, max-age=300", "X-Content-Type-Options": "nosniff"},
        )

    @app.get("/preview/{embed_id}/{number}")
    def preview(embed_id: str, number: int, exp: int = 0, sig: str = "") -> Response:
        """Any Version, for the journalist's preview. 404 unless signed and unexpired."""
        valid = previews.is_valid(embed_id, number, exp, sig)
        return serve(store.version(embed_id, number) if valid else None)

    @app.get("/progress-frame")
    def progress_frame() -> Response:
        return HTMLResponse(progress_page, headers=embed_headers(settings))

    return app
