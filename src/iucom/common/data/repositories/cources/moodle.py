from typing import Any

from aiohttp import ClientSession

from iucom.common.domains.cources.entities import CourseEntity
from iucom.common.domains.cources.enums import CourseDegree, CourseType
from iucom.common.domains.cources.errors import CoursesError

__all__ = ("CoursesMoodleRepository",)


class CoursesMoodleRepository:
    def __init__(self, iu_sso_client_id: str, u_sso_client_secret: str) -> None:
        self.__iu_sso_client_id = iu_sso_client_id
        self.__iu_sso_client_secret = u_sso_client_secret

    async def get_from_moodle(self) -> list[CourseEntity]:
        entities = []
        for course in await self.__get_moodle_data():
            if course["idnumber"] == "":
                continue

            match course["type_course"]:
                case "humanitaric elective":
                    course["type_course"] = CourseType.HUMANITARIAN_ELECTIVE

                case "technical elective":
                    course["type_course"] = CourseType.TECHNICAL_ELECTIVE

                case "core":
                    course["type_course"] = CourseType.CORE

                case _:
                    course["type_course"] = CourseType.UNKNOWN

            entities.append(
                CourseEntity(
                    id=course["idnumber"].upper().strip(),
                    moodle=course["moodle_id"],
                    type=course["type_course"] if course["type_course"] is not None else CourseType.UNKNOWN,
                    year=course["year"],
                    degree=course["degree"] if course["degree"] is not None else CourseDegree.UNKNOWN,
                    short_name=course["short_name"].strip(),
                    full_name=course["full_name"].strip(),
                )
            )

        return entities

    async def __get_moodle_data(self) -> list[dict[str, Any]]:
        async with ClientSession() as session, session.post(
            "https://sso.university.innopolis.ru/adfs/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.__iu_sso_client_id,
                "client_secret": self.__iu_sso_client_secret,
            },
        ) as response:
            if response.status != 200:  # noqa: PLR2004
                message = f"Invalid response ({response.status}): {await response.text()}"
                raise CoursesError(message)

            # Parse response.
            data = await response.json()

        async with ClientSession() as session, session.get(
            "https://digitalprofile.innopolis.university/api/courses/list",
            headers={"Authorization": f"Bearer {data['access_token']}"},
        ) as response:
            if response.status != 200:  # noqa: PLR2004
                message = f"Invalid response ({response.status}): {await response.text()}"
                raise CoursesError(message)

            return await response.json()
