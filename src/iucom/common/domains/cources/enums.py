from enum import Enum

__all__ = ("CourseType", "CourseDegree")


class CourseType(str, Enum):
    UNKNOWN = "unknown"
    CORE = "core"
    TECHNICAL_ELECTIVE = "technical_elective"
    HUMANITARIAN_ELECTIVE = "humanitarian_elective"


class CourseDegree(str, Enum):
    UNKNOWN = "unknown"
    MASTERS = "masters"
    BACHELORS = "bachelors"
