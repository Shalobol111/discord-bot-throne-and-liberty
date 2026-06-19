from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DISCORD_TOKEN: str
    GUILD_ID: int
    DKP_LOG_CHANNEL_ID: int
    # NoDecode — отключает авто-парсинг JSON, чтобы наш валидатор разобрал "123,456"
    OFFICER_ROLE_IDS: Annotated[list[int], NoDecode] = []
    DATABASE_URL: str = "sqlite+aiosqlite:///dkp.db"
    DKP_DECAY_PERCENT: int = 5

    @field_validator("OFFICER_ROLE_IDS", mode="before")
    @classmethod
    def parse_role_ids(cls, v: str | list) -> list[int]:
        if isinstance(v, list):
            return v
        return [int(x.strip()) for x in str(v).split(",") if x.strip()]


settings = Settings()
