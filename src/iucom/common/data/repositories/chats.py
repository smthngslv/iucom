import dataclasses
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Any, AsyncContextManager, AsyncIterator
from uuid import UUID

from pymongo import ASCENDING, IndexModel

from iucom.common.data.storages.mongodb import MongoDBStorage
from iucom.common.domains.chats.entities import ChatEntity
from iucom.common.domains.chats.enums import ChatStatus
from iucom.common.domains.chats.errors import ChatsError, ChatsModifiedError, ChatsNotFoundError
from iucom.common.utils import AsyncLazyObject

__all__ = ("ChatsRepository",)


class ChatsRepository(AsyncLazyObject):
    async def __ainit__(self, storage: MongoDBStorage, *, collection: str = "chats") -> None:
        self.__storage = storage
        self.__collection = storage.client[collection]

        await self.__collection.create_indexes(
            [
                IndexModel((("id", ASCENDING),), name="chats_id_idx", unique=True),
                IndexModel((("course", ASCENDING),), name="chats_course_idx"),
                IndexModel((("updated", ASCENDING),), name="chats_updated_idx"),
            ]
        )

    async def get(self, *, id_: UUID | None = None, telegram_entity: int | None = None) -> ChatEntity | None:
        if (id_ is None) == (telegram_entity is None):
            message = "You should provide id or telegram_entity."
            raise ChatsError(message)

        entity = await self.__collection.find_one(
            {"id": str(id_)} if id_ is not None else {"telegram_entity": telegram_entity}  # type: ignore[dict-item]
        )

        if entity is None:
            return None

        return ChatEntity(**entity)

    async def filter(  # noqa: A003
        self, *, exclude_synced: bool = False, course: str | None = None
    ) -> AsyncIterator[ChatEntity]:
        query: dict[str, Any] = {}

        if course is not None:
            query["course"] = course

        if exclude_synced:
            query["status"] = {"$ne": ChatStatus.SYNCED.value}

        async for entity in self.__collection.find(query, sort=[("updated", ASCENDING)]):
            yield ChatEntity(**entity)

    async def insert(self, entity: ChatEntity) -> None:
        await self.__collection.insert_one(self.__serialize(entity))

    @asynccontextmanager
    async def update(self, id_: UUID) -> AsyncIterator[ChatEntity]:
        old_entity = await self.get(id_=id_)

        if old_entity is None:
            message = f"Cannot find a chat with id '{id_}'."
            raise ChatsNotFoundError(message)

        # Yield to modify.
        async with self.__update(old_entity) as new_entity:
            yield new_entity

    async def update_by_filter(
        self, *, exclude_synced: bool = False, course: str | None = None
    ) -> AsyncIterator[AsyncContextManager[ChatEntity]]:
        async for entity in self.filter(exclude_synced=exclude_synced, course=course):
            yield self.__update(entity)

    async def delete(self, id_: UUID) -> bool:
        result = await self.__collection.delete_one({"id": str(id_)})
        return result.deleted_count == 1

    async def shutdown(self) -> None:
        await self.__storage.shutdown()

    @staticmethod
    def __serialize(entity: ChatEntity) -> dict[str, Any]:
        serialized = asdict(entity)

        # UUID.
        serialized["id"] = str(serialized["id"])

        # Milliseconds.
        serialized["updated"] = int(entity.updated.timestamp() * 1000)

        return serialized

    @asynccontextmanager
    async def __update(self, new_entity: ChatEntity) -> AsyncIterator[ChatEntity]:
        # Copy entity before changing.
        old_entity = dataclasses.replace(new_entity)

        # Yield to modify.
        yield new_entity

        is_modified = False
        for field in dataclasses.fields(ChatEntity):
            if getattr(old_entity, field.name) != getattr(new_entity, field.name):
                is_modified = True
                break

        if not is_modified:
            return

        # Update, using transaction.
        result = await self.__collection.update_one(
            {"id": str(old_entity.id), "updated": int(old_entity.updated.timestamp() * 1000)},
            {"$set": self.__serialize(new_entity)},
        )

        # Unsuccessful.
        if result.modified_count == 0:
            message = f"Chat with id '{old_entity}' has been modified."
            raise ChatsModifiedError(message)
