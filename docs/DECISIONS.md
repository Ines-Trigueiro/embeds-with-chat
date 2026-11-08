# Decision note

**1. Readers are protected by the browser, not by trusting the model** ([ADR 0001](adr/0001-sandboxed-iframe-on-separate-origin.md)). Embeds run in `<iframe sandbox="allow-scripts">` without `allow-same-origin`, on a separate origin, with a CSP (`connect-src 'none'`, `sandbox`) that also holds when an embed URL is opened directly. One allowlist (pinned Chart.js, Leaflet and D3, plus OpenStreetMap tiles) generates both the CSP and the system prompt. A Playwright test publishes a hostile embed and proves it can't read the article's cookie or DOM, or redirect the reader.
*Considered:* sanitising the HTML and inlining it in the article, rejected because one miss exposes every reader.

**2. Figures come from the file, never from the model** ([ADR 0002](adr/0002-datasets-injected-by-server.md)). The model sees a dataset's columns and five sample rows, and writes an empty `data-dataset` marker that the server fills with the full rows. A retyped number that is silently wrong is the worst failure for a newsroom.
*Considered:* the whole CSV in the prompt, rejected because it is costly and invites retyping.

**3. Versions are immutable; only published ones reach readers** ([ADR 0003](adr/0003-only-published-versions-reach-readers.md)). Every reply with HTML is a new version. A snippet follows the newest published version, or is pinned to one. Unpublished versions are previewed through signed URLs that expire after 24 hours.
*Considered:* one mutable document per embed, which would put half-finished edits live.

**4. The model loads best-practice guides itself.** The system prompt and five per-type guides (quiz, calculator, chart, map, timeline) are markdown files a non-developer can edit, fetched by the model with a `load_guide` tool. The reply contract is prose plus at most one ` ```html ` document: no HTML means a question, and a broken reply creates no version. The model only sees the latest version, so "make the buttons bigger" means what the journalist sees.
*Considered:* every guide in the prompt, which crowds out the request; a classifier call to pick one, which costs an extra call.

**5. The quality check is feedback for the journalist, not the protection for readers.** **Blockers** (resources outside the allowlist, cookie or parent-page access, links, forms, redirects) stop publishing; **warnings** (missing alt text, source line or viewport) need a confirmation. It is simple static analysis that obfuscated code can get past, which is acceptable only because of choice 1.
*Considered:* an LLM reviewer: non-deterministic, slow and hard to test.

## Deliberately left out

- **Manual HTML editing,** because journalists shouldn't need to touch code.
- **Anything that stores reader input,** such as polls, since embeds can't send data.
- **Real authentication,** because a name field was allowed.
- **Other providers,** since LangChain makes switching a one-line change.
