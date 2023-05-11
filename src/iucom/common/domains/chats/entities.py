from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import AnyUrl, Field, validator
from pydantic.dataclasses import dataclass

from iucom.common.domains.chats.enums import ChatStatus, ChatType, SlowMode

__all__ = ("ChatEntity",)


@dataclass
class ChatEntity:
    title: str = Field()
    course: str = Field()
    type: ChatType = Field()  # noqa: A003
    description: str = Field(default="")
    status: ChatStatus = Field(default=ChatStatus.CREATING)
    slow_mode: SlowMode = Field(default=SlowMode.DISABLED)
    all_reactions: bool = Field(default=False)
    telegram_entity: int | None = Field(default=None)
    telegram_invite_link: AnyUrl | None = Field(default=None)
    id: UUID = Field(default_factory=uuid4)  # noqa: A003
    updated: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))

    @validator("updated", always=True)
    def __validate_updated_at(cls, value: datetime) -> datetime:
        return value.astimezone(tz=timezone.utc)
