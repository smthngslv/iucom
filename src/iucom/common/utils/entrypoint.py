import asyncio
from typing import Awaitable, Callable

__all__ = ("entrypoint",)


def entrypoint(function: Callable[[], Awaitable[None]]) -> Callable[[], None]:
    return lambda: asyncio.run(function())  # type: ignore[arg-type]
