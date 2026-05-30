from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Telegram
    telegram_token: str = Field(..., validation_alias="TELEGRAM_TOKEN")
    bot_username: str = Field("@YourBot", validation_alias="BOT_USERNAME")

    # LLM Provider — "claude" or "ollama"
    llm_provider: str = Field("claude", validation_alias="LLM_PROVIDER")

    # Claude
    claude_api_key: str = Field("", validation_alias="CLAUDE_API_KEY")
    claude_model: str = Field("claude-sonnet-4-6", validation_alias="CLAUDE_MODEL")

    # Ollama (fallback)
    ollama_host: str = Field("http://localhost:11434", validation_alias="OLLAMA_HOST")
    ollama_model: str = Field("llama3.2", validation_alias="OLLAMA_MODEL")

    # Memory
    db_path: str = Field("chatbot.db", validation_alias="DB_PATH")
    max_context_tokens: int = Field(4000, validation_alias="MAX_CONTEXT_TOKENS")

    # API
    api_host: str = Field("0.0.0.0", validation_alias="API_HOST")
    api_port: int = Field(8000, validation_alias="API_PORT")


settings = Settings()
