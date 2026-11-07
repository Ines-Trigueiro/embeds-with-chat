"""How published embeds reach readers: the Snippet, Embed URLs, loader.js and resizing.

The Snippet is one <script> tag. loader.js runs on the article page, creates the
sandboxed iframe right after its own tag (ADR 0001), and resizes it when the embed
reports its height. The embed reports through a small script the embed origin injects
when it serves a Version; the stored Version itself is never changed (ADR 0003).
"""

import html
import json
import re

EMBED_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

RESIZE_SCRIPT = """<script>
(() => {
  // Injected by the embed origin: tells the article page how tall this embed is.
  const report = () => window.parent.postMessage(
    { type: "embed-resize", height: Math.ceil(document.documentElement.getBoundingClientRect().height) },
    "*",
  );
  const observer = new ResizeObserver(report);
  observer.observe(document.documentElement);
  if (document.body) observer.observe(document.body);
  window.addEventListener("load", report);
})();
</script>
"""

_BODY_END = re.compile(r"</body\s*>", re.IGNORECASE)


def embed_url(embed_origin: str, embed_id: str, number: int | None = None) -> str:
    """The latest published version, or one pinned version."""
    base = f"{embed_origin}/e/{embed_id}"
    return base if number is None else f"{base}/v/{number}"


def snippet(embed_origin: str, embed_id: str, number: int | None = None) -> str:
    pinned = "" if number is None else f' data-version="{number}"'
    return f'<script src="{embed_origin}/loader.js" data-embed="{embed_id}"{pinned} async></script>'


def with_resize_reporting(document: str) -> str:
    """The document with the resize script added just before </body> (or at the end)."""
    matches = list(_BODY_END.finditer(document))
    if not matches:
        return document + RESIZE_SCRIPT
    at = matches[-1].start()
    return document[:at] + RESIZE_SCRIPT + document[at:]


_LOADER = """(() => {
  // Embeds with chat: turns each <script data-embed> into a sandboxed, self-sizing iframe.
  const EMBED_ORIGIN = __EMBED_ORIGIN__;
  const MIN_HEIGHT = 50;
  const MAX_HEIGHT = 10000;

  const scripts = document.currentScript
    ? [document.currentScript]
    : Array.from(document.querySelectorAll("script[data-embed]"));

  for (const script of scripts) {
    if (script.dataset.embedLoaded) continue;
    script.dataset.embedLoaded = "true";

    const id = script.dataset.embed || "";
    const version = script.dataset.version;
    if (!/^[A-Za-z0-9_-]{1,64}$/.test(id) || (version && !/^[0-9]+$/.test(version))) {
      console.warn("Embed snippet has an invalid data-embed or data-version", script);
      continue;
    }

    const frame = document.createElement("iframe");
    // Sandbox before src: scripts only, so no access to this page, its cookies or the
    // top window, and no popups or navigation.
    frame.setAttribute("sandbox", "allow-scripts");
    frame.setAttribute("referrerpolicy", "no-referrer");
    frame.setAttribute("loading", "lazy");
    frame.title = script.dataset.title || "Interactive element";
    frame.style.cssText = "display:block;width:100%;height:300px;border:0;overflow:hidden;";
    frame.src = EMBED_ORIGIN + "/e/" + id + (version ? "/v/" + version : "");
    script.after(frame);

    window.addEventListener("message", (event) => {
      // Only this iframe may resize this iframe; its origin is opaque, so check the source.
      if (event.source !== frame.contentWindow) return;
      const data = event.data;
      if (!data || data.type !== "embed-resize" || !Number.isFinite(data.height)) return;
      const height = Math.min(Math.max(Math.ceil(data.height), MIN_HEIGHT), MAX_HEIGHT);
      frame.style.height = height + "px";
    });
  }
})();
"""


def loader_js(embed_origin: str) -> str:
    return _LOADER.replace("__EMBED_ORIGIN__", json.dumps(embed_origin))


def test_article_page(embed_origin: str, embed_id: str, number: int | None) -> str:
    """A stand-in news article, to show an embed in place. It sets a cookie the embed must not see."""
    tag = snippet(embed_origin, html.escape(embed_id), number)
    return f"""<!doctype html>
<html lang="nb">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Testartikkel</title>
<style>
  body {{ margin: 0; font-family: Georgia, serif; background: #fff; color: #1c1c1a; }}
  header {{ background: #0f3a63; color: white; padding: 12px 16px; font-family: system-ui, sans-serif; }}
  article {{ max-width: 680px; margin: 0 auto; padding: 16px; font-size: 1.1rem; line-height: 1.6; }}
  h1 {{ font-size: 1.9rem; line-height: 1.2; }}
  .ingress {{ font-weight: bold; }}
  .embed-slot {{ margin: 24px 0; }}
</style>
<script>document.cookie = "reader_session=secret-reader-cookie; path=/";</script>
</head>
<body>
<header>Lokalavisa</header>
<article id="article">
  <h1>Slik påvirker det nye tiltaket deg</h1>
  <p class="ingress">Dette er en testartikkel som viser hvordan en publisert embed ser ut
  midt i en sak. Teksten rundt er bare utfylling.</p>
  <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Integer posuere erat a ante
  venenatis dapibus. Donec ullamcorper nulla non metus auctor fringilla.</p>
  <div class="embed-slot">
    {tag}
  </div>
  <p id="after-embed">Maecenas faucibus mollis interdum. Cras mattis consectetur purus sit amet
  fermentum. Vestibulum id ligula porta felis euismod semper.</p>
</article>
</body>
</html>
"""
