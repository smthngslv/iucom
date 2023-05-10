from typing import Literal

from pydantic import BaseModel, Field

__all__ = ("Status",)


class Status(BaseModel):
    status: Literal["ok"] = Field(default="ok")
