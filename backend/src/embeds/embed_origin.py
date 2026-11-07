"""The embed origin: serves embeds, on a separate origin from the editor (ADR 0001)."""

import json

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse

from embeds.allowlist import content_security_policy
from embeds.config import Settings
from embeds.previews import PreviewSigner, load_or_create_secret
from embeds.store import Store


def embed_headers(settings: Settings) -> dict[str, str]:
    return {
        "Content-Security-Policy": content_security_policy(settings.embed_origin),
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Cache-Control": "no-store",
    }


DRAFT_FRAME = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Draft preview</title>
<style>html, body, iframe { margin: 0; width: 100%; height: 100%; border: 0; display: block; }</style>
</head>
<body>
<iframe id="draft" sandbox="allow-scripts" title="Draft preview"></iframe>
<script>
  // Renders the half-written HTML the editor streams in, inside a nested sandbox.
  // The nested srcdoc document inherits this page's Content-Security-Policy.
  const EDITOR_ORIGIN = __EDITOR_ORIGIN__;
  const frame = document.getElementById("draft");
  window.addEventListener("message", (event) => {
    if (event.origin !== EDITOR_ORIGIN || event.source !== window.parent) return;
    const data = event.data;
    if (data && data.type === "draft" && typeof data.html === "string") frame.srcdoc = data.html;
  });
  window.parent.postMessage({ type: "draft-frame-ready" }, EDITOR_ORIGIN);
</script>
</body>
</html>
"""


def create_embed_app(settings: Settings) -> FastAPI:
    store = Store(settings.database_path)
    signer = PreviewSigner(load_or_create_secret(settings.data_dir))
    app = FastAPI(title="Embeds with chat – embed origin", docs_url=None, redoc_url=None)

    @app.get("/preview/{embed_id}/{number}")
    def preview(embed_id: str, number: int, sig: str = "") -> Response:
        """Any Version, for the journalist's preview. 404 unless the signature is valid."""
        version = store.version(embed_id, number) if signer.verify(embed_id, number, sig) else None
        if version is None:
            raise HTTPException(status_code=404)
        return HTMLResponse(version.html, headers=embed_headers(settings))

    draft_frame = DRAFT_FRAME.replace("__EDITOR_ORIGIN__", json.dumps(settings.app_origin))

    @app.get("/draft-frame")
    def draft_frame_page() -> Response:
        """Live preview while the model writes; the half-written HTML is never stored."""
        return HTMLResponse(draft_frame, headers=embed_headers(settings))

    return app
