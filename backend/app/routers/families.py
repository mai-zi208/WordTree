"""路由层：“只读展示”词族"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import repositories, scheduling, serializer

router = APIRouter(prefix="/api/families", tags=["families"])

# 列表页
@router.get("")
def list_families() -> dict:
    reviews = repositories.reviews()   #一次性取全量进度
    data = [serializer.family_with_state(f, reviews) for f in repositories.list_families()]
    return {"families": data, "dueTotal": sum(f["due"] for f in data),
            "today": scheduling.today()}

# 详情页
@router.get("/{family_id}")
def get_family(family_id: int) -> dict:
    fam = repositories.get_family(family_id)
    if not fam:
        raise HTTPException(404, "没有这个词族")
    return serializer.family_with_state(fam, repositories.reviews())
