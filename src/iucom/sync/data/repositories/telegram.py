from contextlib import suppress
from typing import Awaitable, Callable

from telethon import events
from telethon.errors import ChannelPrivateError, ChatNotModifiedError, FloodWaitError
from telethon.tl.functions.channels import (
    CreateChannelRequest,
    DeleteChannelRequest,
    EditTitleRequest,
    GetFullChannelRequest,
    ToggleSlowModeRequest,
)
from telethon.tl.functions.messages import (
    EditChatAboutRequest,
    GetDialogFiltersRequest,
    SetChatAvailableReactionsRequest,
    UpdateDialogFilterRequest,
)
from telethon.tl.types import (
    ChatReactionsAll,
    ChatReactionsSome,
    DialogFilter,
    DialogFilterDefault,
    PeerChannel,
    PeerUser,
    ReactionEmoji,
)

from iucom.common.data.storages.mongodb import MongoDBStorage
from iucom.sync.data.storages.telegram import TelegramStorage
from iucom.sync.domains.telegram.entities import (
    CreateTelegramEntity,
    TelegramEntity,
    TelegramMessageEntity,
    UpdateTelegramEntity,
)
from iucom.sync.domains.telegram.enums import SlowMode

__all__ = ("TelegramRepository",)


class TelegramRepository:
    NECESSARY_REACTIONS = ChatReactionsSome(list(map(ReactionEmoji, ("🔥", "😢", "👎", "👍", "❤", "🐳"))))

    def __init__(
        self,
        telegram_storage: TelegramStorage,
        mongodb_storage: MongoDBStorage,
        *,
        core_folder_title: str = "Core",
        electives_folder_title: str = "Electives",
        other_folder_title: str = "Other",
        collection: str = "orphans",
    ) -> None:
        self.__telegram_storage = telegram_storage
        self.__mongodb_storage = mongodb_storage
        self.__collection = mongodb_storage.client[collection]

        # Folders.
        self.__core_folder_title = core_folder_title
        self.__electives_folder_title = electives_folder_title
        self.__other_folder_title = other_folder_title

    def add_on_message_handler(self, handler: Callable[[TelegramMessageEntity], Awaitable[None]]) -> None:
        @self.__telegram_storage.client.on(events.NewMessage(incoming=True))
        async def _wrapper(event: events.NewMessage.Event) -> None:
            if not isinstance(event.message.from_id, PeerUser) or not isinstance(event.message.peer_id, PeerChannel):
                return

            await handler(
                TelegramMessageEntity(
                    id=event.message.id,
                    chat=event.message.peer_id.channel_id,
                    user=event.message.from_id.user_id,
                    body=event.message.message,
                    created_at=event.message.date,
                )
            )

    async def get(self, id_: int) -> TelegramEntity | None:
        try:
            result = await self.__telegram_storage.client(
                GetFullChannelRequest(await self.__telegram_storage.client.get_input_entity(id_))
            )

        except (ChannelPrivateError, ValueError):
            return None

        slow_mode = result.full_chat.slowmode_seconds
        if slow_mode is None:
            slow_mode = SlowMode.DISABLED

        return TelegramEntity(
            id=result.full_chat.id,
            title=result.chats[0].title,
            invite_link=result.full_chat.exported_invite.link,
            description=result.full_chat.about,
            is_broadcast=result.chats[0].broadcast,
            all_reactions=isinstance(result.full_chat.available_reactions, ChatReactionsAll),
            slow_mode=slow_mode,
        )

    async def create(self, entity: CreateTelegramEntity) -> TelegramEntity:
        # Create in Telegram.
        result = await self.__telegram_storage.client(
            CreateChannelRequest(
                title=entity.title,
                about=entity.description,
                megagroup=not entity.is_broadcast,
                broadcast=entity.is_broadcast,
            )
        )

        try:
            if not entity.is_broadcast:
                # Permissions.
                await self.__telegram_storage.client.edit_permissions(
                    result.chats[0].id,
                    view_messages=True,
                    send_messages=True,
                    send_media=True,
                    send_stickers=False,
                    send_gifs=False,
                    send_games=False,
                    send_inline=False,
                    embed_link_previews=True,
                    send_polls=True,
                    change_info=False,
                    invite_users=True,
                    pin_messages=False,
                )

        except Exception as exception:
            await self.delete(result.chats[0].id)
            raise exception

        return TelegramEntity(
            id=result.chats[0].id,
            title=entity.title,
            invite_link=None,
            description=entity.description,
            is_broadcast=entity.is_broadcast,
            all_reactions=True,
            slow_mode=SlowMode.DISABLED,
        )

    async def update(self, entity: UpdateTelegramEntity) -> None:
        peer = await self.__telegram_storage.client.get_input_entity(entity.id)

        with suppress(ChatNotModifiedError):
            if entity.all_reactions is not None:
                reactions = ChatReactionsAll() if entity.all_reactions else self.NECESSARY_REACTIONS
                await self.__telegram_storage.client(SetChatAvailableReactionsRequest(peer, reactions))

            if entity.title is not None:
                await self.__telegram_storage.client(EditTitleRequest(peer, entity.title))

            if entity.description is not None:
                await self.__telegram_storage.client(EditChatAboutRequest(peer, entity.description))

            if entity.slow_mode is not None:
                await self.__telegram_storage.client(ToggleSlowModeRequest(peer, entity.slow_mode.value))

    async def delete(self, id_: int, *, robust: bool = True) -> None:
        try:
            await self.__telegram_storage.client(
                DeleteChannelRequest(await self.__telegram_storage.client.get_input_entity(id_))
            )

            # Delete from orphans, if present.
            await self.__collection.delete_many({"id": id_})

        # Channel already deleted.
        except (ChannelPrivateError, ValueError):
            # Delete from orphans, if present.
            await self.__collection.delete_many({"id": id_})

        except FloodWaitError as exception:
            if not robust:
                raise exception

            # Put this to orphans, to delete later.
            await self.__collection.update_one({"id": id_}, {"$set": {"id": id_}}, upsert=True)

    async def delete_orphans(self) -> None:
        async for entity in self.__collection.find({}):
            await self.delete(entity["id"], robust=False)

    async def update_core_folder(self, ids: list[int]) -> None:
        await self.__update_folder(self.__core_folder_title, ids)

    async def update_electives_folder(self, ids: list[int]) -> None:
        await self.__update_folder(self.__electives_folder_title, ids)

    async def update_other_folder(self, ids: list[int]) -> None:
        await self.__update_folder(self.__other_folder_title, ids)

    async def shutdown(self) -> None:
        await self.__telegram_storage.shutdown()
        await self.__mongodb_storage.shutdown()

    async def __update_folder(self, folder_title: str, entity_ids: list[int]) -> None:
        ids = {1, 2}
        folder_id = None

        # Find existing folder.
        for folder in await self.__telegram_storage.client(GetDialogFiltersRequest()):
            # Skip default.
            if isinstance(folder, DialogFilterDefault):
                continue

            # If folder already exists.
            if folder.title == folder_title:
                folder_id = folder.id
                break

            ids.add(folder.id)

        # Folder does not exist, need to find proper id first.
        if folder_id is None:
            # If there is any available id, then use it.
            for id_ in range(2, max(ids)):
                if id_ not in ids:
                    folder_id = id_
                    break

            # If no available, then just use next one.
            if folder_id is None:
                folder_id = max(ids) + 1

        # Clearing.
        # TODO: Deleting folder throws INPUT_METHOD_INVALID_472471681_289215.
        if len(entity_ids) == 0:
            me = await self.__telegram_storage.client.get_me(input_peer=True)
            entity_ids = [me.user_id]

        # Update / Create folder.
        await self.__telegram_storage.client(
            UpdateDialogFilterRequest(
                folder_id,
                DialogFilter(
                    folder_id,
                    folder_title,
                    pinned_peers=[],
                    include_peers=[await self.__telegram_storage.client.get_input_entity(id_) for id_ in entity_ids],
                    exclude_peers=[],
                ),
            )
        )
