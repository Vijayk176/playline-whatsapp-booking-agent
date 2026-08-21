from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    secret_key: str = "change-this"
    database_url: str = "sqlite:///./odyssey.db"

    ai_provider: str = "groq"
    groq_api_key: str = ""

    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = "change-this-verify-token"
    whatsapp_business_account_id: str = ""

    admin_username: str = "admin"
    admin_password: str = "change-this-password"

    timezone: str = "Asia/Karachi"


settings = Settings()
