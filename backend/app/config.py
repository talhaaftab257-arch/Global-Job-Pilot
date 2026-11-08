from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    frontend_url: str = "http://localhost:5173"
    employer_boards: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    smtp_email: str = ""
    smtp_password: str = ""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""

settings = Settings()
