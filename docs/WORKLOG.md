# Work log

Notes on how I steered the coding assistant (Claude Code) during this assignment.

## 1. Design interview (before any code)

I had the assistant interview me in rounds about the design, with a recommended answer for every question, before any code was written. The output was `GLOSSARY.md` and three ADRs in `docs/adr/`.

Where I overrode its recommendations:
- **Frontend**: it recommended server-rendered Jinja templates with a little JS, to keep me in Python. I chose a React + TypeScript SPA.
- **Scope**: it recommended doing the core first, then building extensions in priority order and cutting what didn't fit the time. I chose to build all three: streaming, attachments and quality checks.
- **Manual editing**: I rejected it outright, because journalists should not touch code.
- **Images**: it recommended images only as content in the embed. I want them as content and as a visual reference for the model.
- **Language**: it proposed a Norwegian UI. I asked for a nb/da/en switch. The assistant then separated the journalist's chat language from the embed's language, and I accepted that.
- **Model**: Claude is the default, but any LangChain-supported model can be selected through an env var.

Where it pushed back on me:
- It warned that the combined scope (SPA + LangChain + streaming + attachments + quality checks) is large for 4–6 hours. I kept the scope.
- It asked me to clarify "skills". They became **Guides**: markdown best-practice files the model loads through a tool, named that way to avoid confusion with Claude Code skills.
- It pointed out that pinning versions in the snippet changes what "publish" means. The result: only explicitly published versions reach readers.

## 2. Ticket #1: skeleton

- The assistant built the slice test-first through the HTTP API, with the chat model injected so tests run against a fake.
- I had it run a two-axis review (standards and spec, as separate sub-agents) before moving on. The review caught two real bugs:
  - **Names outside Latin-1 broke every request.** The journalist's name was sent as an HTTP header, which browsers refuse for those characters. A journalist named "Łukasz" got past the prompt and then every request failed. Fixed by URL-encoding the name, test first.
  - **A `.gitignore` rule didn't match.** The path for the built frontend was anchored at the wrong place.
- The review also caught code drifting from the glossary ("user" instead of "Journalist"). I had it rename, and add *Editor origin* and *Embed origin* to the glossary.
- I kept the unused hooks for the chat model and settings that the review flagged as speculative, because ticket #2 uses them straight away.

## 3. Ticket #2: chat, versions and the sandboxed preview

- The assistant proposed two designs the ticket hadn't specified, and I accepted both:
  - **Signed preview URLs**, so the journalist can preview versions that aren't published from the embed origin.
  - **A separate frame on the embed origin for work in progress**, so half-written HTML runs under the same CSP as finished versions.
- The two-axis review then found real problems in exactly those designs:
  - **Preview URLs never expired.** A leaked URL would have exposed a version that was never published, permanently. Fixed by signing an expiry, and I had ADR 0003 amended rather than silently contradicted.
  - **The sandbox only held inside an iframe.** Opened directly in a tab, the pages ran without it. Fixed by adding `sandbox` to the CSP header itself.
  - **The prompt and the CSP disagreed about images**, despite coming from "one source". Fixed with a test that every CSP source appears in the prompt.
- **Vocabulary:** the review flagged "draft", a word the glossary avoids. We named the concept *Work in progress* and renamed it everywhere.
- **First real run:** I set the local model to Claude Haiku 5.5 to keep costs down. The default stays Sonnet 5.5. The first real run produced a self-contained Norwegian calculator in about 8 seconds, with no external requests.

## 4. Tickets #3–#9: the rest of the core, and all three extensions

- I asked the assistant to "implement all the unblocked tickets and fix what you think is needed". It did them one ticket at a time, each test-first at the agreed seams, with a commit per ticket and a two-axis review after each batch.
- **What the reviews caught, and we fixed:**
  - **The resize message type** didn't match the ticket's contract.
  - **The guide status lines** were lost on reload.
  - **The language rules** sat in code instead of the editable base guide.
  - **A dataset cell containing `<!--`** would have broken the embed for readers, because the escape we used isn't valid JSON.
  - **The quality check blocked ordinary data embeds.** It looked at the injected data as if it were the model's code.
  - **Image URLs were only 48 bits**, short enough to guess.
- **Deliberate deviations, recorded instead of hidden:**
  - **ADR 0002 amendment:** one dataset marker per dataset instead of a single `embed-data` block.
  - **Publishing behind the check in the browser test:** the test publishes a hostile embed past the quality check, because it exists to prove the sandbox holds even when something bad does get published.
- **Proving the tests could fail:** for the browser isolation test, the assistant temporarily weakened the sandbox and confirmed the test caught the cookie leak, before trusting that it passes.
- **Every feature was also tried against the real model (Claude Haiku 5.5):**
  - It loaded the right guide.
  - It kept Danish embed text while chatting in English.
  - It used the dataset marker without retyping any figure.
  - It placed an attached logo by its URL, and followed a sketch without embedding it.
  - Screenshots in Chromium caught two layout problems the tests couldn't: a squeezed preview, and a clipped chart label. The clipped label led to a new rule in the chart guide.
- **Where I accepted a limit rather than over-build:**
  - The quality check can be fooled by obfuscated code. The CSP and sandbox are what protect readers.
  - Nothing yet detects a model that retypes figures from the sample rows.

## 5. Ticket #10: README and decision note

- The assistant proposed which five choices the decision note should lead with, and I approved them. Its reasons: each had a real trade-off and was either already in an ADR or proven by a test.
- The README commands were checked rather than written from memory. That check found a missing variable in `.env.example` (`PREVIEW_TTL_SECONDS`), and confirmed the local-dev command actually runs.
