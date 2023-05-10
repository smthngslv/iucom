from pydantic import Field
from pydantic.dataclasses import dataclass

from iucom.common.domains.cources.enums import CourseDegree, CourseType

__all__ = ("CourseEntity",)


@dataclass
class CourseEntity:
    id: str = Field()  # noqa: A003
    moodle: int | None = Field()
    full_name: str = Field()
    short_name: str = Field()
    year: int | None = Field()
    type: CourseType = Field()  # noqa: A003
    degree: CourseDegree = Field()
