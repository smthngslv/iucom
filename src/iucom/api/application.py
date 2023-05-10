from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from starlette.middleware.gzip import GZipMiddleware

from iucom.common.data.storages.mongodb import MongoDBStorage
from iucom.common.settings import Settings

application = FastAPI(
    title="IUCom API",
    version="1.0.0",
    default_response_class=ORJSONResponse,
    contact={"name": "Ivan Izmailov", "url": "https://t.me/smthngslv", "email": "smthngslv@optic.xyz"},
)

# Allow CORS.
application.add_middleware(
    CORSMiddleware, allow_credentials=True, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)
# Alloy gzip.
application.add_middleware(GZipMiddleware)


settings = Settings()
mongodb_storage = MongoDBStorage(settings.DATABASE_URL, db=settings.DATABASE_NAME)


@application.on_event("startup")
async def on_startup() -> None:
    await mongodb_storage


@application.on_event("shutdown")
async def on_shutdown() -> None:
    await mongodb_storage.shutdown()


# Include views.
from iucom.api.endpoints import router  # noqa: E402

application.include_router(router, prefix="/v1")  # type: ignore[has-type]
