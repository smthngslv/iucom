from enum import Enum
from typing import TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

from iucom.common.domains.chats.entities import ChatEntity
from iucom.common.domains.chats.enums import ChatStatus

__all__ = ("Chat", "Chats", "ChatCreateRequest", "SlowMode", "ChatUpdateRequest")

T = TypeVar("T", bound="Chat")


class SlowMode(int, Enum):
    DISABLED = 0
    MINIMAL = 10
    MEDIUM = 30
    LONG = 60


class ChatType(str, Enum):
    STUDENTS = "Students"
    TA = "TA"
    CHANNEL = "Channel"


class Chat(BaseModel):
    @classmethod
    def from_entity(cls: type[T], entity: ChatEntity) -> T:
        return cls(
            id=entity.id,
            title=entity.title,
            course_id=entity.course,
            type=getattr(ChatType, entity.type.name),
            description=entity.description,
            invite_link=entity.telegram_invite_link,
            status=entity.status,
            slow_mode=getattr(SlowMode, entity.slow_mode.name),
            all_reactions=entity.all_reactions,
        )

    id: UUID = Field()  # noqa: A003
    title: str = Field()
    course_id: str = Field()
    type: ChatType = Field()  # noqa: A003
    description: str = Field()
    invite_link: str | None = Field()
    status: ChatStatus = Field()
    slow_mode: SlowMode = Field()
    all_reactions: bool = Field()


class Chats(BaseModel):
    chats: list[Chat]


class ChatCreateRequest(BaseModel):
    title: str = Field()
    type: ChatType = Field()  # noqa: A003
    course_id: str = Field()
    slow_mode: SlowMode = Field(default=SlowMode.DISABLED)
    all_reactions: bool = Field(default=False)
    description: str = Field(default="")


class ChatUpdateRequest(BaseModel):
    title: str | None = Field(default=None)
    slow_mode: SlowMode | None = Field(default=None)
    all_reactions: bool | None = Field(default=None)
    description: str | None = Field(default=None)
