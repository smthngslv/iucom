import asyncio
from abc import ABC, ABCMeta, abstractmethod
from asyncio import Lock
from collections.abc import Awaitable, Callable, Generator
from inspect import getattr_static, isabstract, iscoroutinefunction, isfunction
from typing import Any, Concatenate, ParamSpec, TypeVar

__all__ = ("AsyncLazyObject", "AsyncLazyObjectMeta")

Self = TypeVar("Self", bound="AsyncLazyObject")
Return = TypeVar("Return")
Params = ParamSpec("Params")


class AsyncLazyObjectMeta(ABCMeta):
    def __new__(
        mcs: type["AsyncLazyObjectMeta"],  # noqa: N804
        name: str,
        bases: tuple[type, ...],
        attributes: dict[str, Any],
    ) -> type:
        # Create target without modifications class.
        cls = super().__new__(mcs, name, bases, attributes)

        # Skip abstract classes.
        if isabstract(cls):
            return cls

        # We cannot define __init__, since it will be takes from AsyncLazyObject.
        if "__init__" in attributes:
            message = "Use __ainit__ instead of __init__ in the class."
            raise AttributeError(message)

        # Go through each attribute.
        for key in dir(cls):
            # Skip reserved methods.
            if key in ("__init__", "__await__", "__ainit__", "__constructor__", "__is_initialized__"):
                continue

            # Use static, to skip any dynamic attributes.
            attribute = getattr_static(cls, key)

            # Simple method, just wrap it.
            if mcs.__is_wrappable_method(attribute):
                attributes[key] = mcs.__wrapper(attribute)
                continue

            # Property can contain up to 3 methods.
            if isinstance(attribute, property):
                functions = []

                for function in (attribute.fget, attribute.fset, attribute.fdel):
                    if function is not None and mcs.__is_wrappable_method(function):
                        functions.append(mcs.__wrapper(function))  # type: ignore[arg-type]

                    else:
                        functions.append(function)  # type: ignore[arg-type]

                # We have to recreate property, since it's readonly.
                attributes[key] = property(*functions)  # type: ignore[arg-type]

        # Return created class with modifications.
        return super().__new__(mcs, name, bases, attributes)

    @staticmethod
    def __wrapper(
        function: Callable[Concatenate[Self, Params], Return | Awaitable[Return]]
    ) -> Callable[Concatenate[Self, Params], Return | Awaitable[Return]]:
        def _sync_wrapper(self: Self, *args: Params.args, **kwargs: Params.kwargs) -> Return:
            if not self.__is_initialized__:
                message = "Object cannot be initialized due to synchronous context."
                raise RuntimeError(message)

            return function(self, *args, **kwargs)  # type: ignore[return-value]

        async def _async_wrapper(self: Self, *args: Params.args, **kwargs: Params.kwargs) -> Return:
            # Retrieve exception or wait for initialization.
            await self.__constructor__()

            return await function(self, *args, **kwargs)  # type: ignore[misc]

        if iscoroutinefunction(function):
            return _async_wrapper

        return _sync_wrapper

    @staticmethod
    def __is_wrappable_method(attribute: Any) -> bool:
        # Wrap only functions, skip any static/class methods, skip already wrapped functions.
        return (
            isfunction(attribute)
            and not isinstance(attribute, classmethod | staticmethod)
            and "AsyncLazyObjectMeta" not in attribute.__qualname__
        )


class AsyncLazyObject(ABC, metaclass=AsyncLazyObjectMeta):
    """Allow use async constructor __ainit__ for the object.

    Allow use async constructor __ainit__ for the object. But still provide possibility to create
    the object in synchronous context.

    Examples:
        >>> class Test(AsyncLazyObject):
        >>>     async def __ainit__(self, a: int, b: int, c: str = "123") -> None:
        >>>         await asyncio.sleep(1)
        >>>         print(a, b, c)
        >>>
        >>>     def sync_f(self) -> None:
        >>>         print("Works!")
        >>>
        >>>     async def async_f(self) -> None:
        >>>         print("Works!")
        >>>
        >>> # Sync creation outside of loop.
        >>> test = Test(1, 2)
        >>>
        >>> async def example_1() -> None:
        >>>     # First async call. The initialization happens here.
        >>>     await test.async_f()
        >>>
        >>>     # OR. The initialization happens here.
        >>>     await test
        >>>     # But this will fail without "await test".
        >>>     test.sync_f()
        >>>
        >>> async def example_2() -> None:
        >>>     # Async creation inside the loop. The initialization happens here.
        >>>     test = await Test(1, 2)
        >>>     # First async call.
        >>>     await test.async_f()
        >>>     # OR fist sync call.
        >>>     test.sync_f()
    """

    @abstractmethod
    # TODO: Fix Any in typing after moving to 3.11.
    async def __ainit__(self, *args: Any, **kwargs: Any) -> None:
        """
        Async constructor for the object.

        Args:
            *args: Any.
            **kwargs: Any.

        Returns: None

        """

    # TODO: Fix Any in typing after moving to 3.11.
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Create an abject.

        Args:
            *args: This args will be passed to __ainit__.
            **kwargs: This kwargs will be passed to __ainit__.
        """
        self.__args = args
        self.__kwargs = kwargs

        # To avoid multiple constructor calls.
        self.__lock: Lock | None = None

        try:
            # Try to get running loop.
            asyncio.get_running_loop()

        # Loop does not exist, cannot run background initialization.
        except RuntimeError:
            self.__constructor_task = None
            return

        # Loop exists, start background initialization.
        self.__constructor_task = asyncio.create_task(self.__ainit__(*self.__args, **self.__kwargs))

    def __await__(self: Self) -> Generator[Any, None, Self]:
        """
        Wait until initialization is complete.

        Returns: Object itself.

        """
        if self.__constructor_task is None:
            self.__constructor_task = asyncio.create_task(self.__ainit__(*self.__args, **self.__kwargs))

        yield from self.__constructor_task.__await__()
        return self

    async def __constructor__(self) -> None:
        """
        Initialize the object.

        Returns: None

        """
        # Initialization has not been started yet.
        if self.__constructor_task is None:
            if self.__lock is None:
                self.__lock = Lock()

            async with self.__lock:
                # Another coroutine took control.
                if self.__constructor_task is not None:
                    # Retrieve exception or wait for initialization.
                    await self.__constructor_task
                    return

                # Current coroutine has control.
                self.__constructor_task = asyncio.create_task(self.__ainit__(*self.__args, **self.__kwargs))

        # Retrieve exception or wait for initialization.
        await self.__constructor_task
        return

    @property
    def __is_initialized__(self) -> bool:
        """

        Returns: True if object is initialized, False otherwise.

        """
        if self.__constructor_task is not None and self.__constructor_task.done():
            # This will retrieve exception if any.
            self.__constructor_task.result()
            return True

        return False
