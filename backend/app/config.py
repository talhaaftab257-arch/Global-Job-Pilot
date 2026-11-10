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
    supabase_secret_key: str = ""
    frontend_url: str = "http://localhost:5173"
    employer_boards: str = ""
    discord_webhook_url: str = ""
    admin_api_token: str = ""
    local_auth_bypass: bool = True
    smtp_email: str = ""
    smtp_password: str = ""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    openai_api_key: str = ""
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    anthropic_api_key: str = ""
    gemini_api_key: str = ""

    @property
    def supabase_admin_key(self) -> str:
        return self.supabase_secret_key or self.supabase_service_role_key

settings = Settings()
