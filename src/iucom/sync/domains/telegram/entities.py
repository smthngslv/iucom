from datetime import datetime, timezone

from pydantic import AnyUrl, Field, validator
from pydantic.dataclasses import dataclass

from iucom.sync.domains.telegram.enums import SlowMode

__all__ = ("TelegramUpdateEntity", "TelegramCreateEntity", "TelegramEntity", "TelegramMessageEntity")


@dataclass
class TelegramUpdateEntity:
    id: int = Field()  # noqa: A003
    title: str | None = Field(default=None)
    description: str | None = Field(default=None)
    all_reactions: bool | None = Field(default=None)
    slow_mode: SlowMode | None = Field(default=None)


@dataclass
class TelegramCreateEntity:
    title: str = Field()
    description: str = Field(default="")
    is_broadcast: bool = Field(default=False)


@dataclass
class TelegramEntity:
    id: int = Field()  # noqa: A003
    title: str = Field()
    invite_link: AnyUrl | None = Field()
    description: str = Field()
    is_broadcast: bool = Field()
    all_reactions: bool = Field()
    slow_mode: SlowMode = Field()


@dataclass
class TelegramMessageEntity:
    id: int = Field()  # noqa: A003
    chat: int = Field()
    user: int = Field()
    body: str = Field()
    created_at: datetime = Field()

    @validator("created_at", always=True)
    def __validate_updated_at(cls, value: datetime) -> datetime:
        return value.astimezone(tz=timezone.utc)
