from functools import lru_cache

from pydantic import EmailStr, Field, PostgresDsn, SecretStr, TypeAdapter
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_DB = TypeAdapter(PostgresDsn).validate_python(
    "postgresql://user:pass@localhost:5432/db"
)


class Settings(BaseSettings):
    app_name: str = "Al Qasr Backend"
    app_env: str = "development"
    app_version: str = "1.0.0"
    debug: bool = True

    # Example database configuration
    database_url: PostgresDsn = DEFAULT_DB

    imagekit_id: SecretStr = Field(default=...)
    imagekit_public_key: SecretStr = Field(default=...)
    imagekit_private_key: SecretStr = Field(default=...)

    admin_email: EmailStr = Field(default=...)
    admin_password: SecretStr = Field(default=...)

    jwt_secret: SecretStr = Field(default=...)
    jwt_access_token_expire_minutes: int = Field(default=...)

    allowed_origins: list[str] = Field(default=["http://localhost:5000"])

    # Read configuration from a local .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Use lru_cache to ensure the configuration is loaded and validated exactly once
@lru_cache
def get_settings() -> Settings:
    return Settings()
