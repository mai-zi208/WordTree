"""Spaced-repetition scheduling. Intervals, rating effects and family rollback."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

INTERVALS = [0, 1, 2, 4, 7, 15, 30]
ROLLBACK_MIN = 3
RATINGS = ("fast", "back", "long", "gone")


def ymd(day: date) -> str:
    return day.isoformat()


def today() -> str:
    return ymd(date.today())


def plus(days: int) -> str:
    return ymd(date.today() + timedelta(days=days))


def next_stage(stage: int, rating: str) -> int:
    if rating == "fast":
        return stage + 1
    if rating == "back":
        return stage + 1 if stage < 4 else stage
    if rating == "long":
        return max(stage, 1)
    return 1


def apply_rating(record: Optional[dict], rating: str) -> dict:
    """Return the review row to persist for one word after a self-rating."""
    stage = (record or {}).get("stage", 0)
    wrong = (record or {}).get("wrong", 0)
    stage = min(next_stage(stage, rating), len(INTERVALS) - 1)
    if rating == "gone":
        wrong += 1
    return {"stage": stage, "next_date": plus(INTERVALS[stage]), "wrong": wrong}


def rollback_stage() -> int:
    return min(1, len(INTERVALS) - 1)


def rollback_date() -> str:
    return plus(INTERVALS[rollback_stage()])
