__all__ = ("ChatsError", "ChatsNotFoundError", "ChatsModifiedError", "ChatsCannotModifyError", "ChatsInvalidError")


class ChatsError(Exception):
    pass


class ChatsInvalidError(ChatsError):
    pass


class ChatsNotFoundError(ChatsError):
    pass


class ChatsModifiedError(ChatsError):
    pass


class ChatsCannotModifyError(ChatsError):
    pass
