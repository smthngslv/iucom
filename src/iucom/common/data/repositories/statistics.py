from dataclasses import asdict
from typing import Any

from pymongo import ASCENDING, IndexModel

from iucom.common.data.storages.mongodb import MongoDBStorage
from iucom.common.domains.statistics.entities import StatisticsEntryEntity
from iucom.common.utils import AsyncLazyObject

__all__ = ("StatisticsRepository",)


class StatisticsRepository(AsyncLazyObject):
    async def __ainit__(self, storage: MongoDBStorage, *, collection: str = "statistics") -> None:
        self.__storage = storage
        self.__collection = storage.client[collection]

        await self.__collection.create_indexes(
            [
                IndexModel((("id", ASCENDING),), name="statistics_id_idx", unique=True),
                IndexModel((("user", ASCENDING),), name="statistics_user_idx"),
                IndexModel((("chat", ASCENDING),), name="statistics_chat_idx"),
            ]
        )

    async def insert(self, entity: StatisticsEntryEntity) -> None:
        await self.__collection.insert_one(self.__serialize(entity))

    async def shutdown(self) -> None:
        await self.__storage.shutdown()

    @staticmethod
    def __serialize(entity: StatisticsEntryEntity) -> dict[str, Any]:
        serialized = asdict(entity)

        # UUID.
        serialized["id"] = str(serialized["id"])
        serialized["user"] = str(serialized["user"])
        serialized["chat"] = str(serialized["chat"])

        # Milliseconds.
        serialized["updated"] = int(entity.created_at.timestamp() * 1000)

        return serialized
