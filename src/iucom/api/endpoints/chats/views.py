import csv
from io import StringIO
from typing import Any, AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Body, File, Header, HTTPException, Path, Query, status
from starlette.responses import StreamingResponse

from iucom.api.application import mongodb_storage
from iucom.api.endpoints.chats.schemas import Chat, ChatCreateRequest, Chats
from iucom.common.data.repositories.chats import ChatsRepository
from iucom.common.domains.chats.entities import ChatEntity
from iucom.common.domains.chats.enums import ChatType, SlowMode
from iucom.common.domains.chats.interactors import ChatsInteractor

__all__ = ("router",)

router = APIRouter(tags=["chats"])

repository = ChatsRepository(mongodb_storage)
interactor = ChatsInteractor(repository)


async def _generate_csv_file(*, course_id: str | None = None) -> AsyncIterator[bytes]:
    def _encode(*data: Any) -> bytes:
        with StringIO() as buffer:
            csv.writer(buffer).writerow(data)
            return buffer.getvalue().encode()

    # Header.
    yield _encode("course_id", "invite_link", "title", "type", "slow_mode", "all_reactions", "description")

    # Return all courses.
    async for chat in interactor.filter(course=course_id):
        serialized_chat = Chat.from_entity(chat)

        yield _encode(
            serialized_chat.course_id,
            serialized_chat.invite_link,
            serialized_chat.title,
            serialized_chat.type,
            serialized_chat.slow_mode.value,
            serialized_chat.all_reactions,
            serialized_chat.description,
        )


@router.get("", response_model=Chats, description="Returns all chats for the course.")
async def get(course_id: str | None = Query(default=None), accept: str = Header(default="application/json")) -> Chats:
    if accept == "text/csv":
        return StreamingResponse(
            _generate_csv_file(course_id=course_id),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="chats.csv"'},
        )  # type: ignore[return-value]

    return Chats(chats=[Chat.from_entity(entity) async for entity in interactor.filter(course=course_id)])


@router.put("", response_model=Chat, description="Create a new chat.")
async def create(request: ChatCreateRequest = Body()) -> Chat:
    chat = ChatEntity(
        title=request.title.strip(),
        type=getattr(ChatType, request.type.name),
        course=request.course_id.upper().strip(),
        slow_mode=getattr(SlowMode, request.slow_mode.name),
        all_reactions=request.all_reactions,
        description=request.description.strip(),
    )
    await interactor.create(chat)
    return Chat.from_entity(chat)


@router.post("", description="Imports courses from csv file.")
async def import_(file: bytes = File()) -> None:
    with StringIO(file.decode()) as buffer:
        for i, line in enumerate(csv.reader(buffer)):
            try:
                course_id, title, type_, slow_mode, all_reactions, description = line

                chat = ChatCreateRequest(
                    title=title.strip(),
                    type=type_,  # type: ignore[arg-type]
                    course_id=course_id.upper().strip(),
                    slow_mode=int(slow_mode),  # type: ignore[arg-type]
                    all_reactions=all_reactions,  # type: ignore[arg-type]
                    description=description.strip(),
                )

            except Exception as exception:
                # This is probably header, skip it.
                if i == 0:
                    continue

                raise HTTPException(
                    detail=f"Cannot parse line: {exception}. Line should be in a form: 'course_id, title, type_, "
                    f"slow_mode, all_reactions, description'",
                    status_code=status.HTTP_400_BAD_REQUEST,
                ) from exception

            await interactor.create(
                ChatEntity(
                    title=chat.title,
                    type=getattr(ChatType, chat.type.name),
                    course=chat.course_id,
                    slow_mode=getattr(SlowMode, chat.slow_mode.name),
                    all_reactions=chat.all_reactions,
                    description=chat.description,
                )
            )


@router.delete("/{id:uuid}", status_code=status.HTTP_204_NO_CONTENT, description="Delete a chat.")
async def delete(id_: UUID = Path(alias="id")) -> None:
    await interactor.delete(id_)


@router.on_event("startup")
async def on_startup() -> None:
    await repository


@router.on_event("shutdown")
async def on_shutdown() -> None:
    await interactor.shutdown()
