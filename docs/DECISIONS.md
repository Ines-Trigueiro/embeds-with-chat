# Decision note

**1. Readers are protected by the browser, not by trusting the model** ([ADR 0001](adr/0001-sandboxed-iframe-on-separate-origin.md)). Embeds run in `<iframe sandbox="allow-scripts">` without `allow-same-origin`, served from a separate origin. They also carry a CSP with `connect-src 'none'` and `sandbox`, so the protection holds even when an embed URL is opened directly. One allowlist (pinned Chart.js, Leaflet and D3, plus OpenStreetMap tiles) generates both the CSP and the system prompt, so the model is told exactly what the browser will enforce. A Playwright test publishes a hostile embed and proves it can't read the article's cookie or DOM, or redirect the reader. Mutating the sandbox makes the test fail.
*Considered:* sanitising the HTML and inlining it in the article, rejected because one miss exposes every reader; banning all external resources, rejected because it rules out maps.

**2. Figures come from the file, never from the model** ([ADR 0002](adr/0002-datasets-injected-by-server.md)). The model sees a dataset's columns and five sample rows. It writes an empty `data-dataset` marker, and the server fills it with the full rows when the version is created. When the version is shown back to the model, the marker is emptied again. A retyped number that is silently wrong is the worst failure for a newsroom.
*Considered:* putting the whole CSV in the prompt, rejected because it is costly and invites retyping.

**3. Versions are immutable; only published ones reach readers** ([ADR 0003](adr/0003-only-published-versions-reach-readers.md)). Every reply with HTML is a new version. A snippet follows the newest published version, or is pinned with `data-version`. The journalist previews unpublished versions through signed URLs that expire after 24 hours, so a leaked preview link stops working.
*Considered:* one mutable document per embed, rejected because a half-finished edit would go live in an article already published.

**4. The model loads best-practice guides itself.** The base guide (the system prompt) and five per-type guides (quiz, calculator, chart, map, timeline) are markdown files a non-developer can edit. The model fetches the relevant one with a `load_guide` tool, and the chat shows which one it read. The reply contract is simple: prose, plus at most one complete ` ```html ` document. A reply with no HTML is a question; a broken reply creates no version. The model always sees only the latest version's HTML, so "make the buttons bigger" means what the journalist sees.
*Considered:* putting every guide in the prompt, which is simpler but crowds out the request; a classifier call to pick the guide, which costs an extra call.

**5. The quality check is feedback for the journalist, not the protection for readers.** Every version is checked as soon as it is created.
- **Blockers** stop publishing: resources outside the allowlist, cookie or parent-page access, links, forms, redirects, oversized documents.
- **Warnings** need a confirmation: missing alt text, no source line, no viewport.

It is deliberately simple static analysis, and obfuscated code can get past it. That is acceptable only because of choice 1. The browser test publishes behind the check's back to prove readers stay safe anyway.
*Considered:* a second LLM call to review each embed, rejected because it is non-deterministic, hard to test and slow.

## Deliberately left out

- **Manual HTML editing,** because journalists shouldn't need to touch code.
- **Anything that stores reader input,** such as polls, since embeds can't send data.
- **Real authentication,** because a name field was allowed.
- **More than one provider installed.** Claude is the default, and LangChain makes switching a one-line change plus a package.

## What I would do next

- **Catch retyped figures:** warn when numbers from a dataset's sample rows appear literally in the code.
- **Visual regression:** render every new version headlessly at 320px and flag horizontal overflow or clipped text. Screenshots caught two such problems during development that no test did.
- **Access control:** real login, sharing embeds within a desk, and unpublishing.
- **Harden the quality check:** parse scripts properly with a JS parser instead of using patterns, and check dates as well as sources.
