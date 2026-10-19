"""Route layer: queues, ratings and scheduling commits."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import question_builder, repositories, scheduling, schemas

router = APIRouter(prefix="/api/study", tags=["study"])


@router.get("/due")
def due() -> dict:
    words = question_builder.due_words()
    return {"today": scheduling.today(), "count": len(words),
            "words": [w["word"] for w in words]}


@router.post("/queue")
def queue(body: schemas.QueueRequest) -> dict:
    if body.mode == "review":
        words = question_builder.due_words()
        per_word = 1
        if not words:
            raise HTTPException(409, "今天没有到期的词")
    else:
        if body.family_id is None:
            raise HTTPException(422, "练习模式需要 familyId")
        fam = repositories.get_family(body.family_id)
        if not fam:
            raise HTTPException(404, "没有这个词族")
        words = question_builder.pool_words(fam, body.pool)
        per_word = 2 if body.pool == "fresh" else 1
    items = question_builder.build_queue(words, per_word)
    if not items:
        raise HTTPException(409, "这一组没有可练的词")
    return {"mode": body.mode,
            "familyId": body.family_id,
            "pool": body.pool if body.mode == "practice" else "due",
            "items": items}


@router.post("/commit")
def commit(body: schemas.CommitRequest) -> dict:
    scheduled, forgot = [], {}
    for r in body.results:
        w = repositories.get_word(r.word)
        if not w:
            raise HTTPException(422, f"词库里没有 {r.word}")
        rec = scheduling.apply_rating(repositories.review(r.word), r.rating)
        repositories.save_review(r.word, rec)
        scheduled.append({"word": r.word, "stage": rec["stage"], "nextDate": rec["next_date"]})
        if r.rating == "gone":
            forgot[w["family_id"]] = forgot.get(w["family_id"], 0) + 1

    rolled = [fid for fid, n in forgot.items() if n >= scheduling.ROLLBACK_MIN]
    for fid in rolled:
        repositories.rollback_family(fid)
    if rolled:
        recs = repositories.reviews()
        for s in scheduled:
            live = recs.get(s["word"])
            if live:
                s["stage"], s["nextDate"] = live["stage"], live["next_date"]

    if body.family_id is not None:
        fam = repositories.get_family(body.family_id)
        dates = repositories.next_dates_for(body.family_id)
        next_date = dates[0] if dates else None
        root = fam["root"] if fam else None
    else:
        next_date, root = repositories.earliest_next(), None
    return {"scheduled": scheduled,
            "rolledBackRoots": [repositories.get_family(fid)["root"] for fid in rolled],
            "familyRoot": root, "nextDate": next_date}


@router.delete("/progress")
def reset() -> dict:
    repositories.reset_progress()
    return {"cleared": True}
