from fastapi import APIRouter

__all__ = ("router",)

router = APIRouter()

from iucom.api.endpoints.chats.views import router as chats  # noqa: E402
from iucom.api.endpoints.courses.views import router as courses  # noqa: E402
from iucom.api.endpoints.system.views import router as system  # noqa: E402

router.include_router(system, prefix="/system")
router.include_router(chats, prefix="/chats")
router.include_router(courses, prefix="/courses")
