from enum import Enum
from typing import TypeVar

from pydantic import BaseModel, Field

from iucom.common.domains.cources.entities import CourseEntity
from iucom.common.domains.cources.enums import CourseDegree as _CourseDegree, CourseType as _CourseType

__all__ = ("Course", "Courses")

T = TypeVar("T", bound="Course")


class CourseType(str, Enum):
    CORE = "core"
    TECHNICAL_ELECTIVE = "technical elective"
    HUMANITARIC_ELECTIVE = "humanitaric elective"


class CourseDegree(str, Enum):
    MASTERS = "masters"
    BACHELORS = "bachelors"


class Course(BaseModel):
    @classmethod
    def from_entity(cls: type[T], entity: CourseEntity) -> T:
        match entity.type:
            case _CourseType.UNKNOWN:
                type_ = None

            case _CourseType.HUMANITARIAN_ELECTIVE:
                type_ = CourseType.HUMANITARIC_ELECTIVE

            case _:
                type_ = getattr(CourseType, entity.type.name)

        return cls(
            id=entity.id,
            full_name=entity.full_name,
            short_name=entity.short_name,
            year=entity.year,
            moodle_id=entity.moodle,
            type=type_,
            degree=getattr(CourseDegree, entity.degree.name) if entity.degree != _CourseDegree.UNKNOWN else None,
        )

    id: str = Field()  # noqa: A003
    full_name: str = Field()
    short_name: str = Field()
    year: int | None = Field()
    moodle_id: int | None = Field()
    type: CourseType | None = Field()  # noqa: A003
    degree: CourseDegree | None = Field()

    def to_entity(self) -> CourseEntity:
        match self.type:
            case None:
                type_ = _CourseType.UNKNOWN

            case CourseType.HUMANITARIC_ELECTIVE:
                type_ = _CourseType.HUMANITARIAN_ELECTIVE

            case _:
                type_ = getattr(_CourseType, self.type.name)

        return CourseEntity(
            id=self.id,
            moodle=self.moodle_id,
            full_name=self.full_name,
            short_name=self.short_name,
            year=self.year,
            type=type_,
            degree=getattr(_CourseDegree, self.degree.name) if self.degree is not None else _CourseDegree.UNKNOWN,
        )


class Courses(BaseModel):
    courses: list[Course] = Field()
