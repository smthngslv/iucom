import csv
from io import StringIO
from typing import Any, AsyncIterator

from fastapi import APIRouter, File, Header, HTTPException, Path, status
from starlette.responses import StreamingResponse

from iucom.api.application import mongodb_storage
from iucom.api.endpoints.courses.schemas import Course, Courses
from iucom.common.data.repositories.cources import CoursesMongoDBRepository
from iucom.common.domains.cources.interactors import CoursesInteractor

__all__ = ("router",)

router = APIRouter(tags=["courses"])
repository = CoursesMongoDBRepository(mongodb_storage)
interactor = CoursesInteractor(repository)


async def _generate_csv_file() -> AsyncIterator[bytes]:
    def _encode(*data: Any) -> bytes:
        with StringIO() as buffer:
            csv.writer(buffer).writerow(data)
            return buffer.getvalue().encode()

    # Header.
    yield _encode("id", "moodle_id", "full_name", "short_name", "year", "type", "degree")

    # Return all courses.
    async for course in interactor.filter():
        serialized_course = Course.from_entity(course)

        yield _encode(
            serialized_course.id,
            serialized_course.moodle_id,
            serialized_course.full_name,
            serialized_course.short_name,
            serialized_course.year,
            serialized_course.type,
            serialized_course.degree,
        )


@router.get("", description="Returns all courses.")
async def get(accept: str = Header(default="application/json")) -> Courses:
    if accept == "text/csv":
        return StreamingResponse(
            _generate_csv_file(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="courses.csv"'},
        )  # type: ignore[return-value]

    return Courses(courses=[Course.from_entity(course) async for course in interactor.filter()])


@router.delete("/{id:str}", status_code=status.HTTP_204_NO_CONTENT, description="Delete a course.")
async def delete(id_: str = Path(alias="id")) -> None:
    await interactor.delete(id_)


@router.post("", description="Imports courses from csv file.")
async def import_(file: bytes = File()) -> None:
    with StringIO(file.decode()) as buffer:
        for i, line in enumerate(csv.reader(buffer)):
            try:
                id_, moodle_id, full_name, short_name, year, type_, degree = line

                course = Course(
                    id=id_.upper().strip(),
                    moodle_id=moodle_id if moodle_id != "" else None,  # type: ignore[arg-type]
                    full_name=full_name.strip(),
                    short_name=short_name.strip(),
                    year=year if year != "" else None,  # type: ignore[arg-type]
                    type=type_ if type_ != "" else None,  # type: ignore[arg-type]
                    degree=degree if degree != "" else None,  # type: ignore[arg-type]
                )

            except Exception as exception:
                # This is probably header, skip it.
                if i == 0:
                    continue

                raise HTTPException(
                    detail=f"Cannot parse line: {exception}. Line should be in a form: 'id, moodle_id, full_name, "
                    f"short_name, year, type, degree'",
                    status_code=status.HTTP_400_BAD_REQUEST,
                ) from exception

            await interactor.upsert(course.to_entity())


@router.on_event("startup")
async def on_startup() -> None:
    await repository


@router.on_event("shutdown")
async def on_shutdown() -> None:
    await interactor.shutdown()
