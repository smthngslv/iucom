from dataclasses import asdict
from typing import AsyncIterator

from pymongo import ASCENDING, IndexModel

from iucom.common.data.storages.mongodb import MongoDBStorage
from iucom.common.domains.cources.entities import CourseEntity
from iucom.common.utils import AsyncLazyObject

__all__ = ("CoursesMongoDBRepository",)


class CoursesMongoDBRepository(AsyncLazyObject):
    async def __ainit__(self, storage: MongoDBStorage, *, collection: str = "courses") -> None:
        self.__storage = storage
        self.__collection = storage.client[collection]
        await self.__collection.create_indexes([IndexModel((("id", ASCENDING),), name="courses_id_idx", unique=True)])

    async def get(self, id_: str) -> CourseEntity | None:
        entity = await self.__collection.find_one({"id": str(id_)})

        if entity is None:
            return None

        return CourseEntity(**entity)

    async def filter(self) -> AsyncIterator[CourseEntity]:  # noqa: A003
        async for entity in self.__collection.find({}):
            yield CourseEntity(**entity)

    async def upsert(self, entity: CourseEntity) -> None:
        await self.__collection.update_one({"id": entity.id}, {"$set": asdict(entity)}, upsert=True)

    async def delete(self, id_: str) -> bool:
        result = await self.__collection.delete_one({"id": id_})
        return result.deleted_count == 1

    async def shutdown(self) -> None:
        await self.__storage.shutdown()
