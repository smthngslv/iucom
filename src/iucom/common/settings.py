from pathlib import Path

from pydantic import BaseSettings, Field, MongoDsn

__all__ = ("Settings",)


class Settings(BaseSettings):
    DATABASE_URL: MongoDsn = Field(default="mongodb://iucom:iucom@localhost")
    DATABASE_NAME: str = Field(default="iucom")

    # Telegram.
    TELEGRAM_API_ID: int | None = Field(default=None)
    TELEGRAM_API_HASH: str | None = Field(default=None)
    TELEGRAM_SESSION: Path = Field(default=Path("./sessions/main"))
    TELEGRAM_SYNC_PERIOD: int = Field(default=60)
    TELEGRAM_FULL_SYNC_PERIOD: int = Field(default=1800)
    TELEGRAM_CORE_FOLDER: str = Field(default="Core")
    TELEGRAM_ELECTIVES_FOLDER: str = Field(default="Electives")
    TELEGRAM_OTHER_FOLDER: str = Field(default="Other")

    # Digital Profile API.
    IU_SSO_CLIENT_ID: str | None = Field(default=None)
    IU_SSO_CLIENT_SECRET: str | None = Field(default=None)
    MOODLE_SYNC_PERIOD: int = Field(default=60)

    class Config:
        case_sensitive = False

        env_file = "./.env"
        env_prefix = "IUCOM_"
