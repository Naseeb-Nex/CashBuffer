from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/cashbuffer"
    TELEGRAM_BOT_TOKEN: str = ""
    # Used for encrypting BYO-LLM API keys at rest. (Requires a 32-byte url-safe base64-encoded bytes string)
    ENCRYPTION_KEY: str = "4CNPcPvUHydNCbtN3FM195z4gcREF1Mxb-fqSCeQPHU="
    # Local & MCP JWT Secret for self-hosted mode
    LOCAL_JWT_SECRET: str = ""
    # Allowed CORS Origins (comma-separated, e.g. "https://cashbuffer.example.com,http://localhost:3000")
    ALLOWED_ORIGINS: str = ""
    # Kinde Configurations
    KINDE_DOMAIN: str = ""
    KINDE_CLIENT_ID: str = ""
    KINDE_CLIENT_SECRET: str = ""
    KINDE_CALLBACK_URL: str = "http://localhost:8000/callback"
    # Google OAuth Configurations
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/ingress/gmail/callback"
    GMAIL_OAUTH_STATE_SECRET: str = ""
    WEB_BASE_URL: str = "http://localhost:3001"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
