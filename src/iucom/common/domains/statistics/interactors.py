import dataclasses

from iucom.common.data.repositories.statistics import StatisticsRepository
from iucom.common.domains.statistics.entities import MessageEntity, StatisticsEntryEntity, StatisticsFeaturesEntity

__all__ = ("StatisticsInteractor",)


class StatisticsInteractor:
    def __init__(self, repository: StatisticsRepository) -> None:
        self.__repository = repository

    async def create(self, entity: MessageEntity) -> StatisticsEntryEntity:
        entry = StatisticsEntryEntity(
            **dataclasses.asdict(entity), features=StatisticsFeaturesEntity(length=len(entity.body))
        )

        await self.__repository.insert(entry)
        return entry

    async def shutdown(self) -> None:
        await self.__repository.shutdown()
