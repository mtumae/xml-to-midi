import os

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    APP_NAME: str = "XML TO MIDI Server"
    PORT: int = 8000
    DEBUG: bool = False

    DATABASE_URL: str | None = Field(..., validation_alias="DATABASE_URL")
    REDIS_URL: str | None = Field(..., validation_alias="REDIS_URL")

    R2_ENDPOINT: str | None = Field(..., validation_alias="R2_ENDPOINT")
    R2_BUCKET: str | None = Field(..., validation_alias="R2_BUCKET")
    R2_ACCESS_KEY_ID: str | None = Field(..., validation_alias="R2_ACCESS_KEY_ID")
    R2_SECRET_ACCESS_KEY: str | None = Field(
        ..., validation_alias="R2_SECRET_ACCESS_KEY"
    )
    R2_TOKEN: str | None = Field(..., validation_alias="R2_TOKEN")
    R2_PUBLIC_URL: str | None = Field(..., validation_alias="R2_PUBLIC_URL")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )


settings = Settings(
    APP_NAME="XML TO MIDI Server",
    PORT=8000,
    DEBUG=False,
    DATABASE_URL=os.getenv("DATABASE_URL"),
    REDIS_URL=os.getenv("REDIS_URL"),
    R2_ENDPOINT=os.getenv("R2_ENDPOINT"),
    R2_BUCKET=os.getenv("R2_BUCKET"),
    R2_ACCESS_KEY_ID=os.getenv("R2_ACCESS_KEY_ID"),
    R2_SECRET_ACCESS_KEY=os.getenv("R2_SECRET_ACCESS_KEY"),
    R2_TOKEN=os.getenv("R2_TOKEN"),
    R2_PUBLIC_URL=os.getenv("R2_PUBLIC_URL"),
)
