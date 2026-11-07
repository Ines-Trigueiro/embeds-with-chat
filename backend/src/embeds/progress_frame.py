"""The page that shows work in progress while the model is still writing.

Work in progress is never stored, so it can't be served by URL like a Version.
Instead the editor posts it to this page on the embed origin, which renders it in
a nested sandboxed srcdoc iframe. The srcdoc document inherits this page's
Content-Security-Policy, so work in progress runs under the same rules as a Version.
"""

import json

_PAGE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Work in progress</title>
<style>html, body, iframe { margin: 0; width: 100%; height: 100%; border: 0; display: block; }</style>
</head>
<body>
<iframe id="wip" sandbox="allow-scripts" title="Work in progress"></iframe>
<script>
  const EDITOR_ORIGIN = __EDITOR_ORIGIN__;
  const frame = document.getElementById("wip");
  window.addEventListener("message", (event) => {
    if (event.origin !== EDITOR_ORIGIN || event.source !== window.parent) return;
    const data = event.data;
    if (data && data.type === "progress" && typeof data.html === "string") frame.srcdoc = data.html;
  });
  window.parent.postMessage({ type: "progress-frame-ready" }, EDITOR_ORIGIN);
</script>
</body>
</html>
"""


def progress_frame_page(editor_origin: str) -> str:
    """The page, accepting messages only from the editor origin."""
    return _PAGE.replace("__EDITOR_ORIGIN__", json.dumps(editor_origin))
