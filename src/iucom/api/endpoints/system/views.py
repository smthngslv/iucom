from fastapi import APIRouter

from iucom.api.endpoints.system.schemas import Status

router = APIRouter(
    tags=[
        "system",
    ]
)


@router.get("/status", response_model=Status, description="Returns OK if system if online.")
async def status() -> Status:
    return Status()
