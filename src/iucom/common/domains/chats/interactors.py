import dataclasses
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncContextManager, AsyncIterator
from uuid import UUID

from iucom.common.data.repositories.chats import ChatsRepository
from iucom.common.domains.chats.entities import ChatEntity
from iucom.common.domains.chats.enums import ChatStatus, ChatType, SlowMode
from iucom.common.domains.chats.errors import ChatsCannotModifyError, ChatsInvalidError, ChatsNotFoundError

__all__ = ("ChatsInteractor",)


class ChatsInteractor:
    def __init__(self, repository: ChatsRepository) -> None:
        self.__repository = repository

    async def get(self, *, id_: UUID | None = None, telegram_entity: int | None = None) -> ChatEntity:
        entity = await self.__repository.get(id_=id_, telegram_entity=telegram_entity)

        if entity is None:
            message = f"Chat with id '{id_ if id_ is not None else telegram_entity}' not found."
            raise ChatsNotFoundError(message)

        return entity

    def filter(  # noqa: A003
        self, *, exclude_synced: bool = False, course: str | None = None
    ) -> AsyncIterator[ChatEntity]:
        return self.__repository.filter(exclude_synced=exclude_synced, course=course)

    async def create(self, entity: ChatEntity) -> None:
        if entity.type == ChatType.CHANNEL and entity.slow_mode != SlowMode.DISABLED:
            message = "Channel cannot have slow mode."
            raise ChatsInvalidError(message)

        # Indicate, that we have created it. Just in case.
        entity.status = ChatStatus.CREATING
        entity.updated = datetime.now(tz=timezone.utc)

        await self.__repository.insert(entity)

    async def delete(self, id_: UUID, *, forced: bool = False) -> None:
        if forced:
            # Deleted.
            if await self.__repository.delete(id_):
                return

            message = f"Cannot find a chat with id '{id_}'."
            raise ChatsNotFoundError(message)

        async with self.__repository.update(id_) as entity:
            entity.status = ChatStatus.DELETING
            entity.updated = datetime.now(tz=timezone.utc)

    async def update(self, new_entity: ChatEntity) -> None:
        async with self.__update(self.__repository.update(new_entity.id)) as old_entity:
            for field in dataclasses.fields(ChatEntity):
                setattr(old_entity, field.name, getattr(new_entity, field.name))

    async def update_by_filter(
        self, *, exclude_synced: bool = False, course: str | None = None
    ) -> AsyncIterator[AsyncContextManager[ChatEntity]]:
        async for transaction in self.__repository.update_by_filter(exclude_synced=exclude_synced, course=course):
            yield self.__update(transaction)

    async def shutdown(self) -> None:
        await self.__repository.shutdown()

    @staticmethod
    @asynccontextmanager
    async def __update(transaction: AsyncContextManager[ChatEntity]) -> AsyncIterator[ChatEntity]:
        async with transaction as old_entity:
            # Save copy of old status.
            old_status = old_entity.status
            # Create a copy of old entity.
            new_entity = dataclasses.replace(old_entity)
            # Yield to modify.
            yield new_entity

            # Validate. We cannot change chat type.
            if old_entity.type != new_entity.type:
                message = "Cannot modify chat type."
                raise ChatsCannotModifyError(message)

            # Apply changes.
            is_modified = False
            for field in dataclasses.fields(ChatEntity):
                if getattr(old_entity, field.name) != getattr(new_entity, field.name):
                    is_modified = True
                    setattr(old_entity, field.name, getattr(new_entity, field.name))

            # No changes.
            if not is_modified:
                return

            # Avoiding inconsistent state, do not perform any updating
            if old_status == ChatStatus.DELETING:
                message = "Cannot modify chat while chat mark for deleting."
                raise ChatsCannotModifyError(message)

            # Indicate, that we have change it.
            old_entity.updated = datetime.now(tz=timezone.utc)
