"""纯数据访问层：只封装SQL，不含业务规则（业务在routers/question_builder/scheduling里）"""
from __future__ import annotations

import json
from typing import Any, Optional

from . import scheduling
from .db import session

WORD_COLUMNS = ("id, family_id, word, pos, gloss, part, meme, content_type, content_en, "
                "content_zh, example, blank, img, img_zh, position")
JOINED_COLUMNS = ("words.id, words.family_id, words.word, words.pos, words.gloss, words.part, "
                  "words.meme, "
                  "words.content_type, words.content_en, words.content_zh, words.example, "
                  "words.blank, words.img, words.img_zh, words.position, "
                  "families.family, families.root, families.root_meaning")

# 行结果转成dict列表
def _rows(conn, sql: str, args: tuple = ()) -> list[dict]:
    return [dict(r) for r in conn.execute(sql, args).fetchall()]

def _words(conn, family_id: int) -> list[dict]:
    return _rows(conn, f"SELECT {WORD_COLUMNS} FROM words WHERE family_id=? ORDER BY position",
                 (family_id,))

FAMILY_COLUMNS = "id, family, root, root_meaning, intro, kind, source, created_at"

# 查词族
def list_families() -> list[dict]:
    with session() as conn:
        fams = _rows(conn, f"SELECT {FAMILY_COLUMNS} FROM families ORDER BY id")
        for f in fams:
            f["words"] = _words(conn, f["id"])
        return fams

# 将单词填充进词族
def get_family(family_id: int) -> Optional[dict]:
    with session() as conn:
        fams = _rows(conn, f"SELECT {FAMILY_COLUMNS} FROM families WHERE id=?", (family_id,))
        if not fams:
            return None
        fams[0]["words"] = _words(conn, family_id)
        return fams[0]

# 一次性取回所有单词及词根信息
def all_words() -> list[dict]:
    """Every word with its family carried along, in family/position order."""
    with session() as conn:
        return _rows(conn, f"SELECT {JOINED_COLUMNS} FROM words "
                           "JOIN families ON families.id=words.family_id "
                           "ORDER BY words.family_id, words.position")

# 按单词或按族查
def get_word(word: str) -> Optional[dict]:
    with session() as conn:
        rows = _rows(conn, f"SELECT {WORD_COLUMNS} FROM words WHERE word=?", (word,))
        return rows[0] if rows else None


def family_words(family_id: int) -> list[dict]:
    with session() as conn:
        return _words(conn, family_id)

# 复习进度
def reviews() -> dict[str, dict]:
    with session() as conn:
        return {r["word"]: {"stage": r["stage"], "next_date": r["next_date"], "wrong": r["wrong"]}
                for r in _rows(conn, "SELECT word, stage, next_date, wrong FROM reviews")}


def review(word: str) -> Optional[dict]:
    with session() as conn:
        rows = _rows(conn, "SELECT word, stage, next_date, wrong FROM reviews WHERE word=?", (word,))
        return rows[0] if rows else None


def save_review(word: str, rec: dict) -> None:
    with session() as conn:
        conn.execute(
            "INSERT INTO reviews(word, stage, next_date, wrong, updated_at) "
            "VALUES(?,?,?,?,datetime('now')) "
            "ON CONFLICT(word) DO UPDATE SET stage=excluded.stage, next_date=excluded.next_date, "
            "wrong=excluded.wrong, updated_at=excluded.updated_at",
            (word, rec["stage"], rec["next_date"], rec["wrong"]))


def reset_progress() -> None:
    with session() as conn:
        conn.execute("DELETE FROM reviews")


def rollback_family(family_id: int) -> None:
    stage, when = scheduling.rollback_stage(), scheduling.rollback_date()
    with session() as conn:
        conn.execute(
            "UPDATE reviews SET stage=?, next_date=?, updated_at=datetime('now') "
            "WHERE word IN (SELECT word FROM words WHERE family_id=?) AND stage>?",
            (stage, when, family_id, stage))

# 写入一族单词
def insert_family(conn, fam: dict, source: str) -> Optional[int]:
    """Write one family + its words on the caller's connection. None if the root exists."""
    root = fam["root"]
    if conn.execute("SELECT 1 FROM families WHERE root=?", (root,)).fetchone():
        return None
    cur = conn.execute(
        "INSERT INTO families(family, root, root_meaning, intro, kind, source) "
        "VALUES(?,?,?,?,?,?)",
        (fam.get("family") or root, root, fam["rootMeaning"], fam.get("intro", ""),
         fam.get("kind", "root"), source))
    family_id = cur.lastrowid
    for position, w in enumerate(fam["words"]):
        content = w["content"]
        conn.execute(
            "INSERT INTO words(family_id, word, pos, gloss, part, meme, content_type, "
            "content_en, content_zh, example, blank, img, img_zh, position) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(word) DO NOTHING",
            (family_id, w["word"], w.get("pos", ""), w["gloss"], w["part"], w["meme"],
             content["type"], content["en"], content["zh"], w["example"], w["blank"],
             w.get("img"), w.get("img_zh", ""), position))
    return family_id

# 添加单词
def add_family(fam: dict, source: str) -> Optional[int]:
    with session() as conn:
        return insert_family(conn, fam, source)


def earliest_next() -> Optional[str]:
    with session() as conn:
        row = conn.execute("SELECT MIN(next_date) AS d FROM reviews "
                           "WHERE next_date IS NOT NULL").fetchone()
        return row["d"] if row and row["d"] else None


def next_dates_for(family_id: int) -> list[str]:
    with session() as conn:
        rows = _rows(conn,
                     "SELECT r.next_date AS d FROM reviews r JOIN words w ON w.word=r.word "
                     "WHERE w.family_id=? AND r.next_date IS NOT NULL ORDER BY r.next_date",
                     (family_id,))
        return [r["d"] for r in rows]


def create_job(job_id: str, keyword: str, kind: str = "family", total: int = 0) -> None:
    with session() as conn:
        conn.execute("INSERT INTO generation_jobs(id, status, kind, keyword, total) "
                     "VALUES(?,?,?,?,?)", (job_id, "pending", kind, keyword, total))


def _dump(result: Any) -> Optional[str]:
    return None if result is None else json.dumps(result, ensure_ascii=False)


def succeed_job(job_id: str, family_id: Optional[int] = None, result: Any = None) -> None:
    with session() as conn:
        conn.execute(
            "UPDATE generation_jobs SET status='succeeded', family_id=?, done=total, "
            "result_json=?, error=NULL, updated_at=datetime('now') WHERE id=?",
            (family_id, _dump(result), job_id))


def fail_job(job_id: str, error: str, result: Any = None) -> None:
    with session() as conn:
        conn.execute(
            "UPDATE generation_jobs SET status='failed', error=?, result_json=?, "
            "updated_at=datetime('now') WHERE id=?", (error[:500], _dump(result), job_id))


def running_job(job_id: str) -> None:
    with session() as conn:
        conn.execute("UPDATE generation_jobs SET status='running', updated_at=datetime('now') "
                     "WHERE id=?", (job_id,))


def job_progress(job_id: str, done: int, result: Any = None) -> None:
    """Batch jobs publish per-family progress while they run, so the UI can poll it."""
    with session() as conn:
        conn.execute("UPDATE generation_jobs SET done=?, result_json=?, "
                     "updated_at=datetime('now') WHERE id=?", (done, _dump(result), job_id))


def get_job(job_id: str) -> Optional[dict]:
    with session() as conn:
        rows = _rows(conn, "SELECT id, status, kind, keyword, family_id, total, done, "
                           "result_json, error, created_at, updated_at "
                           "FROM generation_jobs WHERE id=?", (job_id,))
        return rows[0] if rows else None


def delete_job(job_id: str) -> None:
    """丢掉一个生成任务：暂存在 result_json 里的词族内容随它一起消失，不进词库。"""
    with session() as conn:
        conn.execute("DELETE FROM generation_jobs WHERE id=?", (job_id,))


def sweep_jobs(hours: int = 24) -> int:
    """清掉超期的任务行。用户直接关浏览器时前端来不及丢弃暂存，靠这个兜底。"""
    with session() as conn:
        cur = conn.execute("DELETE FROM generation_jobs "
                           "WHERE updated_at < datetime('now', ?)", (f"-{int(hours)} hours",))
        return cur.rowcount
