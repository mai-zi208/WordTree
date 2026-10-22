"""是响应输出层(dict→camelCase JSON)，管出参。跟schemas.py是一对的"""
from __future__ import annotations

from typing import Optional

from . import scheduling

# 1、把DB存的图片相对路径转成根路径
def as_url(rel: Optional[str]) -> Optional[str]:
    return "/" + rel.lstrip("/") if rel else None

# 2、单词行变成前端词对象
def word_json(row: dict) -> dict:
    return {
        "word": row["word"],
        "pos": row["pos"],
        "gloss": row["gloss"],
        "part": row["part"],
        "meme": row["meme"],
        "content": {"type": row["content_type"], "en": row["content_en"], "zh": row["content_zh"]},
        "example": row["example"],
        "blank": row["blank"],
        "img": as_url(row["img"]),
        "imgZh": row["img_zh"],
    }

# 3、词族行变成族对象
def family_json(row: dict) -> dict:
    words = [word_json(w) for w in row["words"]]
    return {
        "id": row["id"],
        "family": row["family"],
        "root": row["root"],
        "rootMeaning": row["root_meaning"],
        "intro": row["intro"],
        "kind": row.get("kind", "root"),
        "source": row["source"],
        "words": words,
    }

# 4、学习进度摘要
def family_state(row: dict, reviews: dict[str, dict]) -> dict:
    today = scheduling.today()
    names = [w["word"] for w in row["words"]]
    recs = [reviews[n] for n in names if n in reviews]
    due = [r for r in recs if r["next_date"] and r["next_date"] <= today]
    nexts = sorted(r["next_date"] for r in recs if r["next_date"])
    return {
        "learned": len(recs),
        "total": len(names),
        "due": len(due),
        "stageSum": sum(r["stage"] for r in recs),
        "nextDate": nexts[0] if nexts else None,
    }

# 5、把两个结果拼成一个对象
def family_with_state(row: dict, reviews: dict[str, dict]) -> dict:
    return family_json(row) | family_state(row, reviews)
