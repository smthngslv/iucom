from fastapi import status
from fastapi.responses import ORJSONResponse

from iucom.api.application import application
from iucom.common.domains.chats.errors import ChatsError, ChatsInvalidError, ChatsNotFoundError
from iucom.common.domains.cources.errors import CoursesError, CoursesNotFoundError

__all__ = ("error_handler", "chat_invalid_error_handler", "not_found_error_handler")


@application.exception_handler(ChatsError)
@application.exception_handler(CoursesError)
def error_handler(_, exception: ChatsError) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"{exception.__class__.__name__}: {exception}"},
    )


@application.exception_handler(ChatsInvalidError)
def chat_invalid_error_handler(_, exception: ChatsInvalidError) -> ORJSONResponse:
    return ORJSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": str(exception)})


@application.exception_handler(ChatsNotFoundError)
@application.exception_handler(CoursesNotFoundError)
def not_found_error_handler(_, exception: ChatsNotFoundError | CoursesNotFoundError) -> ORJSONResponse:
    return ORJSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exception)})
