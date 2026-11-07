"""Runtime configuration, read from environment variables and the `.env` file."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_dir: Path = Path("/data")
    app_origin: str = "http://localhost:8000"
    embed_origin: str = "http://localhost:8001"

    # How long a signed preview URL for a Version stays valid. The editor fetches a
    # fresh one whenever an embed is opened.
    preview_ttl_seconds: int = 24 * 60 * 60

    # Any "provider:model" string LangChain's init_chat_model understands.
    llm_model: str = "anthropic:claude-sonnet-5-5"

    langsmith_api_key: str | None = None
    langsmith_project: str = "embeds-with-chat"

    @property
    def database_path(self) -> Path:
        return self.data_dir / "embeds.sqlite3"

    def enable_tracing_if_configured(self) -> None:
        """LangSmith tracing is opt-in: it switches on only when a key is present."""
        if self.langsmith_api_key:
            os.environ["LANGSMITH_TRACING"] = "true"
            os.environ["LANGSMITH_API_KEY"] = self.langsmith_api_key
            os.environ["LANGSMITH_PROJECT"] = self.langsmith_project
