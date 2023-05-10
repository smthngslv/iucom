from pydantic import AnyUrl, Field
from pydantic.dataclasses import dataclass

from iucom.sync.domains.telegram.enums import SlowMode

__all__ = ("UpdateTelegramEntity", "CreateTelegramEntity", "TelegramEntity")


@dataclass
class UpdateTelegramEntity:
    id: int = Field()  # noqa: A003
    title: str | None = Field(default=None)
    description: str | None = Field(default=None)
    all_reactions: bool | None = Field(default=None)
    slow_mode: SlowMode | None = Field(default=None)


@dataclass
class CreateTelegramEntity:
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
