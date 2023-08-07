import asyncio
import hashlib
from logging import getLogger
from uuid import UUID, uuid4

from iucom.common.domains.chats.entities import ChatEntity
from iucom.common.domains.chats.enums import ChatStatus, ChatType
from iucom.common.domains.chats.errors import ChatsNotFoundError
from iucom.common.domains.chats.interactors import ChatsInteractor
from iucom.common.domains.cources.enums import CourseType
from iucom.common.domains.cources.errors import CoursesNotFoundError
from iucom.common.domains.cources.interactors import CoursesInteractor
from iucom.common.domains.statistics.entities import MessageEntity
from iucom.common.domains.statistics.interactors import StatisticsInteractor
from iucom.sync.data.repositories.telegram import TelegramRepository
from iucom.sync.domains.telegram.entities import (
    TelegramCreateEntity,
    TelegramEntity,
    TelegramMessageEntity,
    TelegramUpdateEntity,
)
from iucom.sync.domains.telegram.enums import SlowMode

__all__ = ("TelegramInteractor",)


class TelegramInteractor:
    def __init__(
        self,
        telegram_repository: TelegramRepository,
        chats_interactor: ChatsInteractor,
        courses_interactor: CoursesInteractor,
        statistics_interactor: StatisticsInteractor,
    ) -> None:
        self.__telegram_repository = telegram_repository
        self.__chats_interactor = chats_interactor
        self.__courses_interactor = courses_interactor
        self.__statistics_interactor = statistics_interactor
        self.__logger = getLogger(f"iucom.{self.__class__.__name__}")

    def setup_on_message_callback(self) -> None:
        self.__telegram_repository.add_on_message_handler(self.__on_message)

    async def sync(self, *, exclude_synced: bool = False) -> None:  # noqa: PLR0912, PLR0915
        self.__logger.info(f"Syncing... Exclude synced objects: {exclude_synced}.")

        is_new_chats_added = False
        async for transaction in self.__chats_interactor.update_by_filter(exclude_synced=exclude_synced):
            telegram_entity = None

            try:
                async with transaction as chat_entity:
                    self.__logger.info(f"Syncing: {chat_entity}.")
                    telegram_entity = await self.__sync(chat_entity)
                    self.__logger.info(f"Synced: {chat_entity}.")

                # If __sync function returns an entity, then the chat was created/recreated.
                is_new_chats_added = is_new_chats_added or telegram_entity is not None

            except Exception as exception:
                self.__logger.exception(f"Exception: {exception}.")

                # No need to delete any orphans.
                if telegram_entity is None:
                    continue

                try:
                    # This means, that chat was created, but bound chat entity was modified.
                    # So delete orphan chat.
                    self.__logger.exception(f"Deleting orphan: {telegram_entity}.")
                    await self.__telegram_repository.delete(telegram_entity.id)
                    self.__logger.exception("Deleted.")

                except Exception as exception:
                    self.__logger.exception(f"Exception: {exception}.")

        try:
            self.__logger.info("Deleting orphans...")
            await self.__telegram_repository.delete_orphans()
            self.__logger.info("Deleted.")

        except Exception as exception:
            self.__logger.exception(f"Exception: {exception}.")

        # If there are no new chats and this is not a full sync
        # then we do not need to update folder.
        if not is_new_chats_added and exclude_synced:
            self.__logger.info("Synced.")
            return

        core_ids = []
        electives_ids = []
        other_ids = []
        async for entity in self.__chats_interactor.filter():
            if entity.telegram_entity is None:
                continue

            try:
                course = await self.__courses_interactor.get(entity.course)

            # Course was deleted.
            except CoursesNotFoundError:
                other_ids.append(entity.telegram_entity)
                continue

            match course.type:
                case CourseType.CORE:
                    core_ids.append(entity.telegram_entity)

                case CourseType.TECHNICAL_ELECTIVE:
                    electives_ids.append(entity.telegram_entity)

                case CourseType.HUMANITARIAN_ELECTIVE:
                    electives_ids.append(entity.telegram_entity)

                case _:
                    other_ids.append(entity.telegram_entity)

        try:
            # Update folder.
            self.__logger.info("Syncing core folder...")
            await self.__telegram_repository.update_core_folder(core_ids)
            self.__logger.info("Synced.")

        except Exception as exception:
            self.__logger.exception(f"Exception: {exception}.")

        try:
            # Update folder.
            self.__logger.info("Syncing electives folder...")
            await self.__telegram_repository.update_electives_folder(electives_ids)
            self.__logger.info("Synced.")

        except Exception as exception:
            self.__logger.exception(f"Exception: {exception}.")

        try:
            # Update folder.
            self.__logger.info("Syncing other folder...")
            await self.__telegram_repository.update_other_folder(other_ids)
            self.__logger.info("Synced.")

        except Exception as exception:
            self.__logger.exception(f"Exception: {exception}.")

        self.__logger.info("Synced.")

    async def shutdown(self) -> None:
        await self.__telegram_repository.shutdown()
        await self.__chats_interactor.shutdown()

    @staticmethod
    def __get_title(entity: ChatEntity) -> str:
        match entity.type:
            case ChatType.STUDENTS:
                return f"{entity.title} Students"

            case ChatType.TA:
                return f"{entity.title} TAs"

            case _:
                return entity.title

    async def __sync(self, chat_entity: ChatEntity) -> TelegramEntity | None:
        # Do not need to check anything.
        if chat_entity.status == ChatStatus.DELETING:
            if chat_entity.telegram_entity is not None:
                self.__logger.info("Deleting telegram entity...")
                await self.__telegram_repository.delete(chat_entity.telegram_entity)
                self.__logger.info("Deleted.")

            self.__logger.info("Deleting chat entity...")
            await self.__chats_interactor.delete(chat_entity.id, forced=True)
            self.__logger.info("Deleted.")
            return None

        # If no telegram entity, then just create it.
        if chat_entity.telegram_entity is None:
            # Create, update id and invite link.
            # Return, to be able to delete orphan if transaction fails.
            self.__logger.info("Creating telegram entity...")
            telegram_entity = await self.__create(chat_entity)
            self.__logger.info(f"Created: {telegram_entity}")

            return telegram_entity

        # Try to get current state.
        self.__logger.info("Retrieving telegram entity...")
        telegram_entity = await self.__telegram_repository.get(chat_entity.telegram_entity)  # type: ignore[assignment]
        self.__logger.info(f"Retrieved: {telegram_entity}")

        # No entity, it was deleted.
        if telegram_entity is None:
            # Create, update id and invite link.
            # Return, to be able to delete orphan if transaction fails.
            self.__logger.info("Creating telegram entity...")
            telegram_entity = await self.__create(chat_entity)
            self.__logger.info(f"Created: {telegram_entity}")
            return telegram_entity

        # Avoid flood.
        await asyncio.sleep(5)

        # Prepare update.
        update = TelegramUpdateEntity(id=telegram_entity.id)

        # Validate title.
        target_title = self.__get_title(chat_entity)
        if telegram_entity.title != target_title:
            self.__logger.info(f"Updating title: {telegram_entity.title} -> {target_title}.")
            update.title = target_title

        # Validate description.
        if telegram_entity.description != chat_entity.description:
            self.__logger.info(f"Updating description: {telegram_entity.description} -> {chat_entity.description}.")
            update.description = chat_entity.description

        # Validate all_reactions.
        if telegram_entity.all_reactions != chat_entity.all_reactions:
            self.__logger.info(
                f"Updating all reactions: {telegram_entity.all_reactions} -> {chat_entity.all_reactions}."
            )
            update.all_reactions = chat_entity.all_reactions

        # Validate slow_mode.
        target_slow_mode = getattr(SlowMode, chat_entity.slow_mode.name)
        if telegram_entity.slow_mode != target_slow_mode:
            self.__logger.info(f"Updating slow mode: {telegram_entity.slow_mode} -> {target_slow_mode}.")
            update.slow_mode = target_slow_mode

        # Sync.
        self.__logger.info(f"Updating... Request: {update}.")
        await self.__telegram_repository.update(update)
        self.__logger.info("Updated.")

        chat_entity.status = ChatStatus.SYNCED
        chat_entity.telegram_entity = telegram_entity.id
        chat_entity.telegram_invite_link = telegram_entity.invite_link

        return None

    async def __create(self, entity: ChatEntity) -> TelegramEntity:
        telegram_entity = await self.__telegram_repository.create(
            TelegramCreateEntity(
                title=self.__get_title(entity),
                description=entity.description,
                is_broadcast=entity.type == ChatType.CHANNEL,
            )
        )

        entity.status = ChatStatus.UPDATING
        entity.telegram_entity = telegram_entity.id
        entity.telegram_invite_link = telegram_entity.invite_link

        return telegram_entity

    async def __on_message(self, message: TelegramMessageEntity) -> None:
        try:
            chat = await self.__chats_interactor.get(telegram_entity=message.chat)

        except ChatsNotFoundError:
            return

        await self.__statistics_interactor.create(
            MessageEntity(
                # If we need to be able to link real message and the message in db,
                # then we need to use hash. But for now, use just random ids.
                id=uuid4(),
                chat=chat.id,
                # To be able to determine most active users, etc., we need to robust id.
                user=UUID(bytes=hashlib.md5(str(message.user).encode()).digest()),  # noqa: S324
                body=message.body,
                created_at=message.created_at,
            )
        )
