# Embeds run in a sandboxed iframe on a separate origin with an allowlist CSP

Embed HTML is written by a model on behalf of a non-developer and shown to many readers, so we treat it as untrusted. Readers see it in `<iframe sandbox="allow-scripts">` without `allow-same-origin`, `allow-top-navigation` or `allow-popups`, which puts it in an opaque origin: it cannot read the article page's cookies or DOM, and it cannot navigate the top window. On top of that, embeds are served from a separate origin (`EMBED_ORIGIN`) with a strict CSP: `connect-src 'none'`, and scripts, styles and images only from a short allowlist (pinned cdnjs libraries, OpenStreetMap tiles, our own embed origin). The system prompt lists the same allowlist, so the browser enforces what the model was asked to follow. The iframe adjusts its height only through `postMessage` to a loader script that accepts messages only from its own iframe's `contentWindow`.

## Considered options

- **Sanitising the HTML and inlining it on the article page**: rejected, because sanitising interactive JS is unreliable, and one miss exposes every reader.
- **No external resources at all** (`default-src 'none'`): safest, but it rules out maps and charts, which are core use cases.

## Consequences

- Embeds cannot send data anywhere, so polls and anything else that stores reader input are out of scope.
- The editor preview uses the same sandbox and CSP, so what the journalist sees is what readers get.
