"""Request bodies only. Responses are plain dicts shaped by the routers."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Mode = Literal["review", "practice"]
Pool = Literal["fresh", "due", "weak", "all"]
RatingKey = Literal["fast", "back", "long", "gone"]


def _camel(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(w.title() for w in rest)


class Request(BaseModel):
    """JSON arrives in camelCase, matching the shapes the frontend already uses."""
    model_config = ConfigDict(alias_generator=_camel, populate_by_name=True,
                               extra="forbid", str_strip_whitespace=True)


class QueueRequest(Request):
    mode: Mode = "practice"
    family_id: Optional[int] = None
    pool: Pool = "all"


class RatingResult(Request):
    word: str = Field(min_length=1, max_length=64)
    rating: RatingKey


class CommitRequest(Request):
    results: list[RatingResult] = Field(min_length=1, max_length=60)
    family_id: Optional[int] = None


class GenerateRequest(Request):
    keyword: str = Field(min_length=1, max_length=40)
    words: int = Field(default=5, ge=3, le=6)
