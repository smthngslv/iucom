from enum import Enum

__all__ = ("ChatType", "SlowMode", "ChatStatus")


class ChatType(str, Enum):
    TA = "ta"
    CHANNEL = "channel"
    STUDENTS = "students"


class SlowMode(str, Enum):
    DISABLED = "disabled"
    MINIMAL = "minimal"
    MEDIUM = "medium"
    LONG = "long"


class ChatStatus(str, Enum):
    SYNCED = "synced"
    CREATING = "creating"
    DELETING = "deleting"
    UPDATING = "updating"
