from datetime import datetime, timezone
from uuid import UUID

from pydantic import Field, validator
from pydantic.dataclasses import dataclass

__all__ = ("MessageEntity", "StatisticsFeaturesEntity", "StatisticsEntryEntity")


@dataclass
class MessageEntity:
    id: UUID = Field()  # noqa: A003
    chat: UUID = Field()
    user: UUID = Field()
    body: str = Field()
    created_at: datetime = Field()

    @validator("created_at", always=True)
    def __validate_updated_at(cls, value: datetime) -> datetime:
        return value.astimezone(tz=timezone.utc)


@dataclass
class StatisticsFeaturesEntity:
    length: int = Field()


@dataclass
class StatisticsEntryEntity:
    id: UUID = Field()  # noqa: A003
    chat: UUID = Field()
    user: UUID = Field()
    features: StatisticsFeaturesEntity = Field()
    created_at: datetime = Field()

    @validator("created_at", always=True)
    def __validate_updated_at(cls, value: datetime) -> datetime:
        return value.astimezone(tz=timezone.utc)
