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
    # Longest single answer, in tokens (~4 chars each). Higher = longer, slower answers.
    claude_max_tokens: int = Field(1024, validation_alias="CLAUDE_MAX_TOKENS")
    # Smaller, faster model that rewrites long answers into a short spoken version
    claude_speech_model: str = Field("claude-haiku-4-5-20251001", validation_alias="CLAUDE_SPEECH_MODEL")

    # Ollama (fallback)
    ollama_host: str = Field("http://localhost:11434", validation_alias="OLLAMA_HOST")
    ollama_model: str = Field("llama3.2", validation_alias="OLLAMA_MODEL")

    # Voice Provider — "elevenlabs" or "none"
    voice_provider: str = Field("elevenlabs", validation_alias="VOICE_PROVIDER")
    elevenlabs_api_key: str = Field("", validation_alias="ELEVENLABS_API_KEY")
    elevenlabs_voice_id: str = Field("", validation_alias="ELEVENLABS_VOICE_ID")
    elevenlabs_stt_model: str = Field("scribe_v2", validation_alias="ELEVENLABS_STT_MODEL")
    elevenlabs_tts_model: str = Field("eleven_flash_v2_5", validation_alias="ELEVENLABS_TTS_MODEL")
    voice_output_format: str = Field("opus_48000_64", validation_alias="VOICE_OUTPUT_FORMAT")

    # Voice guardrails
    max_tts_chars: int = Field(500, validation_alias="MAX_TTS_CHARS")
    max_voice_seconds: int = Field(120, validation_alias="MAX_VOICE_SECONDS")
    # Replies up to this length with no Markdown structure are spoken as-is (no summary call)
    speak_direct_max_chars: int = Field(350, validation_alias="SPEAK_DIRECT_MAX_CHARS")
    # One JSON line per voice turn (numbers only); empty to disable
    voice_metrics_path: str = Field("voice_metrics.jsonl", validation_alias="VOICE_METRICS_PATH")

    # Memory
    db_path: str = Field("chatbot.db", validation_alias="DB_PATH")
    max_context_tokens: int = Field(4000, validation_alias="MAX_CONTEXT_TOKENS")

    # API
    api_host: str = Field("0.0.0.0", validation_alias="API_HOST")
    api_port: int = Field(8000, validation_alias="API_PORT")


settings = Settings()
