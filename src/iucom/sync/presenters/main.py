import asyncio
import logging.config
from datetime import datetime, timezone

from iucom.common.data.repositories.chats import ChatsRepository
from iucom.common.data.repositories.cources import CoursesMongoDBRepository, CoursesMoodleRepository
from iucom.common.data.repositories.statistics import StatisticsRepository
from iucom.common.data.storages.mongodb import MongoDBStorage
from iucom.common.domains.chats.interactors import ChatsInteractor
from iucom.common.domains.cources.interactors import CoursesInteractor
from iucom.common.domains.statistics.interactors import StatisticsInteractor
from iucom.common.settings import Settings
from iucom.common.utils import entrypoint
from iucom.sync.data.repositories.telegram import TelegramRepository
from iucom.sync.data.storages.telegram import TelegramStorage
from iucom.sync.domains.telegram.interactors import TelegramInteractor

# Set logger config.
logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": True,
        "loggers": {
            "iucom": {"handlers": ["console"], "level": "INFO"},
        },
        "handlers": {"console": {"formatter": "default", "class": "logging.StreamHandler", "level": "INFO"}},
        "formatters": {
            "default": {
                "format": r"%(asctime)s %(levelname)s %(module)s:%(funcName)s:%(lineno)d %(message)s",
            }
        },
    }
)


@entrypoint
async def telegram() -> None:
    settings = Settings()

    mongodb_storage = await MongoDBStorage(settings.DATABASE_URL, db=settings.DATABASE_NAME)

    interactor = TelegramInteractor(
        TelegramRepository(
            await TelegramStorage(settings.TELEGRAM_SESSION, settings.TELEGRAM_API_ID, settings.TELEGRAM_API_HASH),
            mongodb_storage,
            core_folder_title=settings.TELEGRAM_CORE_FOLDER,
            electives_folder_title=settings.TELEGRAM_ELECTIVES_FOLDER,
            other_folder_title=settings.TELEGRAM_OTHER_FOLDER,
        ),
        ChatsInteractor(await ChatsRepository(mongodb_storage)),
        CoursesInteractor(await CoursesMongoDBRepository(mongodb_storage)),
        StatisticsInteractor(await StatisticsRepository(mongodb_storage)),
    )

    # Setup callback on messages.
    interactor.setup_on_message_callback()

    try:
        last_sync = datetime.now(tz=timezone.utc)
        last_full_sync = datetime.now(tz=timezone.utc)

        while True:
            now = datetime.now(tz=timezone.utc)

            if (now - last_sync).total_seconds() > settings.TELEGRAM_SYNC_PERIOD:
                await interactor.sync(exclude_synced=True)
                last_sync = datetime.now(tz=timezone.utc)

            if (now - last_full_sync).total_seconds() > settings.TELEGRAM_FULL_SYNC_PERIOD:
                await interactor.sync()
                last_full_sync = datetime.now(tz=timezone.utc)

            await asyncio.sleep(1)

    finally:
        await interactor.shutdown()


@entrypoint
async def moodle() -> None:
    settings = Settings()

    if settings.IU_SSO_CLIENT_ID is None or settings.IU_SSO_CLIENT_SECRET is None:
        message = "You should specify IU_SSO_CLIENT_ID and IU_SSO_CLIENT_SECRET."
        raise ValueError(message)

    interactor = CoursesInteractor(
        await CoursesMongoDBRepository(await MongoDBStorage(settings.DATABASE_URL, db=settings.DATABASE_NAME)),
        CoursesMoodleRepository(settings.IU_SSO_CLIENT_ID, settings.IU_SSO_CLIENT_SECRET),
    )

    try:
        last_sync = datetime.now(tz=timezone.utc)

        while True:
            now = datetime.now(tz=timezone.utc)

            if (now - last_sync).total_seconds() > settings.MOODLE_SYNC_PERIOD:
                await interactor.sync()
                last_sync = datetime.now(tz=timezone.utc)

            await asyncio.sleep(1)

    finally:
        await interactor.shutdown()
