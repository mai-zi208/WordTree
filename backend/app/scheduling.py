"""间隔重复调用模块，管“某个词什么时候该复习”这件事"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

INTERVALS = [0, 1, 2, 4, 7, 15, 30]   #复习间隔（天）
ROLLBACK_MIN = 3   #触发复习词数
RATINGS = ("fast", "back", "long", "gone")   #用户自评结果


# 1、日期工具。统一用YYYY-MM-DD字符串表示时间。
def ymd(day: date) -> str:
    return day.isoformat()

def today() -> str:
    return ymd(date.today())

def plus(days: int) -> str:
    return ymd(date.today() + timedelta(days=days))


# 2、阶段推进。按评分决定下一个stage。
def next_stage(stage: int, rating: str) -> int:
    if rating == "fast":   #记住了，+1
        return stage + 1
    if rating == "back":   #有印象，stage<4才+1，否则不变
        return stage + 1 if stage < 4 else stage
    if rating == "long":   #模糊，停在1
        return max(stage, 1)
    return 1   #完全忘了，回到1


# 3、落库记录 & 回滚
def apply_rating(record: Optional[dict], rating: str) -> dict:
    """Return the review row to persist for one word after a self-rating."""
    stage = (record or {}).get("stage", 0)
    wrong = (record or {}).get("wrong", 0)
    stage = min(next_stage(stage, rating), len(INTERVALS) - 1)
    if rating == "gone":
        wrong += 1
    return {"stage": stage, "next_date": plus(INTERVALS[stage]), "wrong": wrong}

# 家庭级惩罚
def rollback_stage() -> int:
    return min(1, len(INTERVALS) - 1)

# 回滚
def rollback_date() -> str:
    return plus(INTERVALS[rollback_stage()])
