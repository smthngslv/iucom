from enum import Enum

__all__ = ("SlowMode",)


class SlowMode(int, Enum):
    DISABLED = 0
    MINIMAL = 10
    MEDIUM = 30
    LONG = 60
    HUGE = 300
    GIANT = 900
    MAXIMUM = 3600
