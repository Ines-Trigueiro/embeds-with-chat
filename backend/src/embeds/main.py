"""Production entrypoints, one per origin: `uvicorn embeds.main:editor_app` / `embed_app`."""

from langchain.chat_models import init_chat_model

from embeds.config import Settings
from embeds.editor import create_editor_app
from embeds.embed_origin import create_embed_app

settings = Settings()
settings.enable_tracing_if_configured()

# A full embed document is long; too few tokens and replies are cut off mid-HTML.
chat_model = init_chat_model(settings.llm_model, max_tokens=16_000)

editor_app = create_editor_app(settings, chat_model=chat_model)
embed_app = create_embed_app(settings)
