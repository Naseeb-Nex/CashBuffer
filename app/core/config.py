from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    TELEGRAM_BOT_TOKEN: str = ""
    # Used for encrypting BYO-LLM API keys at rest. (Requires a 32-byte url-safe base64-encoded bytes string)
    ENCRYPTION_KEY: str = "sf8g9SZAT2lW7CHIgD3j5EzImynJZjlJ6-P8JhFN_OI=="

    # Kinde Configurations
    KINDE_DOMAIN: str = ""
    KINDE_CLIENT_ID: str = ""
    KINDE_CLIENT_SECRET: str = ""
    KINDE_CALLBACK_URL: str = "http://localhost:8000/callback"

    class Config:
        env_file = ".env"
        extra = "ignore"  # Safely ignore extra keys in .env


settings = Settings()
