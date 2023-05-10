__all__ = ("TelegramError", "TelegramNotFoundError")


class TelegramError(Exception):
    pass


class TelegramNotFoundError(TelegramError):
    pass
