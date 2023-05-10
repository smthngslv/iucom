from pathlib import Path

from telethon import TelegramClient

from iucom.common.utils import AsyncLazyObject

__all__ = ("TelegramStorage",)


class TelegramStorage(AsyncLazyObject):
    async def __ainit__(
        self, session: str | Path, api_id: int, api_hash: str, *, flood_sleep_threshold: int = 15
    ) -> None:
        self.__client = TelegramClient(Path(session).as_posix(), api_id, api_hash)
        self.__client.flood_sleep_threshold = flood_sleep_threshold
        await self.__client.connect()

    @property
    def client(self) -> TelegramClient:
        return self.__client

    async def shutdown(self) -> None:
        await self.__client.disconnect()
