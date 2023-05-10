from logging import getLogger
from typing import AsyncIterator

from iucom.common.data.repositories.cources import CoursesMongoDBRepository, CoursesMoodleRepository
from iucom.common.domains.cources.entities import CourseEntity
from iucom.common.domains.cources.errors import CoursesNotFoundError, CoursesRepositoryNotProvidedError

__all__ = ("CoursesInteractor",)


class CoursesInteractor:
    def __init__(
        self, mongodb_repository: CoursesMongoDBRepository, moodle_repository: CoursesMoodleRepository | None = None
    ) -> None:
        self.__mongodb_repository = mongodb_repository
        self.__moodle_repository = moodle_repository
        self.__logger = getLogger(f"iucom.{self.__class__.__name__}")

    async def get(self, id_: str) -> CourseEntity:
        entity = await self.__mongodb_repository.get(id_)

        if entity is None:
            message = f"Course with id '{id_}' not found."
            raise CoursesNotFoundError(message)

        return entity

    async def upsert(self, entity: CourseEntity) -> None:
        await self.__mongodb_repository.upsert(entity)

    async def delete(self, id_: str) -> None:
        if await self.__mongodb_repository.delete(id_):
            return

        message = f"Cannot find a course with id '{id_}'."
        raise CoursesNotFoundError(message)

    def filter(self) -> AsyncIterator:  # noqa: A003
        return self.__mongodb_repository.filter()

    async def sync(self) -> None:
        if self.__moodle_repository is None:
            message = "You should provide CoursesMoodleRepository repository to sync."
            raise CoursesRepositoryNotProvidedError(message)

        self.__logger.info("Syncing...")
        for entity in await self.__moodle_repository.get_from_moodle():
            self.__logger.info(f"Syncing... Course: {entity}")
            await self.upsert(entity)
            self.__logger.info("Synced.")

        self.__logger.info("Synced.")

    async def shutdown(self) -> None:
        await self.__mongodb_repository.shutdown()
