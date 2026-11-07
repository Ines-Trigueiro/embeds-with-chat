# Embeds with chat

A tool where a journalist describes an interactive element in a chat (a calculator, a quiz, a chart, a map), watches it take shape in a live preview, and publishes it as a snippet to paste into an article. The code is written by a model on behalf of a non-developer and ends up in front of many readers, so readers are protected by the browser's sandbox, not by trusting the model.

- **[Decision note](docs/DECISIONS.md):** the five most important choices, alternatives, and what was left out.
- **[Work log](docs/WORKLOG.md):** how the coding assistant was steered.
- **[Glossary](GLOSSARY.md)** and **[ADRs](docs/adr/):** the domain language, and the decisions that are hard to reverse.

## Run it

You need Docker and an Anthropic API key.

```sh
cp .env.example .env        # then set ANTHROPIC_API_KEY in .env
docker compose up --build
```

Then open **http://localhost:8000**.

Compose starts the same image twice:
- the **editor origin** on `:8000`, where the journalist works;
- the **embed origin** on `:8001`, which serves embeds to the preview and to readers.

Data (SQLite, attachments) lives in a Docker volume, so it survives restarts. `docker compose down -v` wipes it.

## Try it

1. **Enter a name.** There is no password (see [Assumptions](#assumptions)).
2. **Describe an embed** in the empty chat, e.g. *"Lag en kalkulator for strømkostnad: kWh per måned ganger pris per kWh."*
   - The embed is created with your first message.
   - The model suggests a short title, which shows up in the sidebar straight away.
   - Rename it with the pencil, or by double-clicking it.
3. **Watch it being built.**
   - The reply streams in as Markdown, and the preview fills in while the model writes.
   - Shimmering status lines ("Reading guide: calculator…", "Building the embed…") show what the model is doing.
   - Switch the preview between mobile and desktop with the two icons.
4. **Ask for changes,** e.g. *"Gjør knappene større"*.
   - Every reply with HTML becomes a new version, and you can preview any earlier version.
   - Only the conversation and the embed scroll. The version picker, the publish button and the quality check stay in view.
5. **Optional: attach a file** with the paperclip:
   - A **CSV or XLSX** becomes a dataset. The server puts its figures into the embed, so the model never retypes them.
   - An **image** can be shown in the embed ("use this logo") or used as a reference ("make it look like this").
6. **Optional: change the embed's language** with the flag next to the title.
   - If the embed has a version, it asks first, then translates that version into the new language as a new version, with nothing to type ([ADR 0004](docs/adr/0004-language-change-is-a-translation-version.md)).
   - Dataset values stay exactly as attached.
7. **Check the quality chip** above the preview, and click it for the details.
   - Blockers, such as a script from an unknown site, stop publishing.
   - Warnings, such as a missing alt text or source line, have to be ticked off in the publish dialog.
8. **Publish.** The dialog then shows one big **Copy embed code** button, plus three plain steps for pasting it into an HTML block in the article. "Get embed code" reopens it later. The code is:
   ```html
   <script src="http://localhost:8001/loader.js" data-embed="…" async></script>
   ```
   - It follows the newest published version, so an article updates by itself when you publish again.
   - Under *Advanced*:
     - code pinned to one version (`data-version="3"`);
     - plain URLs (`/e/<id>` and `/e/<id>/v/<n>`), for systems that only take a URL.
9. **Open the test article** ("See how it looks in an article" in the dialog, or `http://localhost:8000/test-article?embed=<id>`).
   - It shows the embed inside a stand-in news article, sized to its content.
   - The page sets a cookie that the embed cannot read.

The sidebar lists your embeds, newest first. A green dot marks a published embed. You can search the list, and collapse it to a rail (on phones it's a drawer, and the editor switches between *Chat* and *Preview*). The colours follow your system's light or dark mode.

The flag dropdown at the bottom of the sidebar switches the UI and the model's chat replies between Norwegian, Danish and English. Each embed has its own *embed language* for what readers see.

## Configuration

All settings come from `.env` (see `.env.example`):

| Variable | Default | |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(required)* | Key for the default model. |
| `LLM_MODEL` | `anthropic:claude-sonnet-5-5` | Any `provider:model` string LangChain's `init_chat_model` understands. |
| `APP_ORIGIN` | `http://localhost:8000` | Where the editor is reachable from the browser. |
| `EMBED_ORIGIN` | `http://localhost:8001` | Where embeds are served from. Must be a different origin (ADR 0001). |
| `DATA_DIR` | `/data` | SQLite database, attachments and the preview-signing secret. |
| `PREVIEW_TTL_SECONDS` | `86400` | How long a preview URL for an unpublished version stays valid. |
| `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT` | *(off)* | LangSmith tracing turns on only when a key is set. |

### Other models

The model is resolved by LangChain. Only the Anthropic integration is installed.

- **A cheaper Claude:** set `LLM_MODEL=anthropic:claude-haiku-5-5`. I used it for development.
- **Another provider:** add its package and key. For OpenAI:
  ```sh
  cd backend && uv add langchain-openai
  ```
  Then set `LLM_MODEL=openai:<model>` and `OPENAI_API_KEY` in `.env`, and rebuild.

The model must support tool calling (for the guides) and image input (for image attachments).

## Tests

```sh
cd backend
uv sync
uv run playwright install chromium   # once; for the browser test
uv run pytest                        # about 110 tests, a few seconds, no API key needed
uv run mypy && uv run mypy tests     # strict typing
```

**What's tested:**
- **The model is always a fake** that streams scripted replies in small chunks and records what it was sent. Tests go through the HTTP API of both origins.
- **The quality check** has its own rule-by-rule tests.
- **One browser test** (`tests/test_reader_isolation.py`) publishes a deliberately hostile embed. In Chromium it proves the embed can't read the article's cookie or DOM, open popups or redirect the reader, and that the iframe sizes itself. It's skipped if Chromium isn't installed.

**Frontend typecheck:**
```sh
cd frontend && npm install && npm run typecheck
```

## Development without Docker

```sh
# Backend: two terminals, one per origin
cd backend
DATA_DIR=../data uv run --env-file ../.env uvicorn embeds.main:editor_app --port 8000 --reload
DATA_DIR=../data uv run --env-file ../.env uvicorn embeds.main:embed_app --port 8001 --reload

# Frontend, with hot reload; /api is proxied to :8000
cd frontend && npm install && npm run dev
```

## Layout

```
backend/src/embeds/
  editor.py         editor origin: the journalist's API, the built frontend, /test-article
  embed_origin.py   embed origin: published embeds, signed previews, loader.js, images
  chat.py           one chat turn: guide tool loop, streaming events, creating a version
  titles.py         the title suggested from the first message
  languages.py      chat and embed languages; <html lang>; the translation request
  context.py        what the model sees each turn
  reply.py          the reply contract: prose plus at most one ```html document
  guides/*.md       base guide (the system prompt) and per-type guides, as editable markdown
  allowlist.py      the only network resources an embed may use; feeds CSP, prompt and check
  quality_check.py  findings that block or warn before publishing
  datasets.py       parsing spreadsheets, injecting their rows into versions
  delivery.py       snippet, embed URLs, loader.js, resize script, test article
  previews.py       signed, expiring preview URLs for unpublished versions
frontend/src/       React + TypeScript; i18n in i18n.ts
```

## Assumptions

- **No real authentication.** The journalist types a name, which is sent in a header. Anyone who knows a name sees that journalist's embeds. A real deployment would use the newsroom's login.
- **Embeds can't send data anywhere** (`connect-src 'none'`). So no polls or anything else that stores reader input. That's deliberate (ADR 0001).
- **Embeds can only use a short allowlist:** Chart.js, Leaflet and D3 at pinned versions, plus OpenStreetMap tiles. Anything else is blocked by the browser and flagged by the quality check.
- **No manual HTML editing.** Journalists shouldn't have to touch code. Changes go through the chat.
- **Single process per origin, SQLite.** Fine for a newsroom tool's load; not built to scale horizontally.
