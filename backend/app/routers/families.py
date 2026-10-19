"""Route layer: word families."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import repositories, scheduling, serializer

router = APIRouter(prefix="/api/families", tags=["families"])


@router.get("")
def list_families() -> dict:
    reviews = repositories.reviews()
    data = [serializer.family_with_state(f, reviews) for f in repositories.list_families()]
    return {"families": data, "dueTotal": sum(f["due"] for f in data),
            "today": scheduling.today()}


@router.get("/{family_id}")
def get_family(family_id: int) -> dict:
    fam = repositories.get_family(family_id)
    if not fam:
        raise HTTPException(404, "没有这个词族")
    return serializer.family_with_state(fam, repositories.reviews())
