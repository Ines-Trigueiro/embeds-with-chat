# Work log

Notes on how I steered the coding assistant (Claude Code) during this assignment.

## Time

About 5 hours in total:
- **About 1 hour** working out the solution with my agentic workflow: the design interview, the tickets and the core build (sections 1–5).
- **About 1 hour** testing the result and taking the UI fixes through the same workflow (section 6).
- **The rest** on and off with the assistant, mostly the clean-up passes (sections 7–8).

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

## 6. Tickets #11–#17: UI overhaul

- **Starting point:** I gave the assistant a list of ten UI complaints: bland colours, too much text, page-level scrolling, no markdown, an unfriendly publish step, and others.
- **Settling the open questions first:** before building anything, it grilled me in two rounds of numbered questions, each with a recommended answer.
  - **The ambiguous request:** I had asked for "the embed should switch languages without a new prompt". The assistant laid out two readings: a reader-facing switcher inside the embed, or the journalist changing the language and getting an automatic translation. I chose the second, which became ADR 0004 and the glossary terms *Translation* and *Title*.
  - **The rest I accepted as recommended:**
    - generic CMS steps instead of one named CMS;
    - publishing in a dialog;
    - a sidebar instead of the My embeds page;
    - a title suggested by the model, with a truncation fallback;
    - no deleting of embeds.
- **Seams agreed before tests:** the backend changes (titles and translation) were built test-first at the HTTP API with the fake model.
  - The assistant proposed generating the title *before* the reply rather than in parallel. That keeps the fake model's scripted replies in a predictable order.
  - Frontend changes were checked with the typecheck and with Playwright screenshots at 1400px and 390px, in light and dark mode.
- **What the screenshots caught:**
  - stretched flags in the dropdown;
  - card padding lost in a CSS rewrite;
  - the new embed's chat about to remount mid-stream when it received its id;
  - a three-row preview bar on phones.
- **Checking against the real model (Haiku):** the assistant ran the new-embed flow and a real translation in the browser, under a separate test journalist, so my demo data stayed clean.
- **What the two-axis review caught:**
  - **The failed-translation bug (both reviewers, independently):** a translation that failed still left a "Translated to Danish" marker, and every later prompt replayed the request. Fixed test-first: a translation now leaves a trace only when it produced a version.
  - **A CSS replace that matched twice,** copying rules into the reduced-motion block.
  - **Glossary drift.** I kept "Copy embed code" as the label journalists see, but code identifiers now say *snippet*.
- **Left as they are, on purpose:**
  - The translation endpoint refuses a same-language request with 409. The UI never sends one.

## 7. A `/simplify` pass over the UI overhaul

Four reviewers (reuse, simplification, efficiency, altitude) went over the code. The fixes, with no change in behaviour:

- **Backend:** `chat_turn`'s `translation` flag became a `translation_turn` of its own. Both share one core that streams the model's reply and stores nothing; each turn decides what to keep.
- **Frontend:** one `Modal` for both dialogs, one `storage` helper, one `changeEmbed` PATCH, and `bySeverity` for the quality check. The versions now live only in the opened embed. The editor reads its embed once, and App remounts it on each navigation, which replaces the `editorKey`/`adopted`/`createdHere` guards. The turn list is split into small components, and Markdown is memoized while a reply streams. Dead icons, i18n keys and CSS are gone.
- **Not done:**
  - **Suggesting the Title in parallel with the reply.** It would cut a model round trip before the first token, but the tests pin the Title event as the first event, and the fake model answers in a fixed order.
  - **Caching parsed datasets.** This predates the overhaul.
  - **Typed column for the translation language.** The language is still stored in the message text; a typed column would change the API.
  - **Nullable title column.** It needs a table-rebuild migration.

## 8. Deepening the modules (spec #18, tickets #19–#25)

An architecture review found five deepening candidates. The spec merged the two frontend candidates into one **Workspace** module, which gives two test seams: HTTP on the backend, and the Workspace with a fake API client on the frontend.

The tickets were built by agents in parallel worktrees where the blocking edges allowed it: #19, #21 and #22 first, then #20, then #23 → #24 → #25.

- **Store** (#19): one lookup for the Version readers may see, and Versions and embeds carry their published state.
- **Version view** (#20): a module that owns the Version view and the publish gate.
- **Turn recording** (#22): a module that records each turn in one transaction. The Title is still announced first, but it is saved with the rest of the turn.
- **Language change** (#21): the server refuses a direct Embed language change once a Version exists.
- **Creating an embed** (#23): returns it opened.
- **Workspace** (#24, #25): a plain TypeScript module that owns the Conversation and the embed metadata. React only renders it. Vitest 3.2.7 is pinned, and the Docker build runs the tests.

**Fixed after review:**
- the stale README layout;
- tests not run in the container;
- a duplicated test helper;
- positional `TurnRecord` arguments;
- the publish outcome tested twice in the route;
- no check that creating needs no second request;
- a Translation the journalist left mid-stream not updating the list's Embed language.

**Left as they are:**
- A PATCH with both a title and a new Embed language on an embed with a Version is refused as a whole. The UI never sends both.
- ADR 0004's rule is checked in three places: the PATCH, the Translation preconditions, and the Workspace. Each guards a different entry point.
- `npm audit` reports advisories in dev-only packages (Vite 7.0–7.3.6, Vitest's tinypool and mocker). Production dependencies report none.
