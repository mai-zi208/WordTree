"""SQLite数据访问层：单个数据库文件，不用ORM，开WAL，只负责连接+建表+迁移"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from . import config


# 1、四张表：词族主表、族内单词、复习进度、异步生成任务表
SCHEMA = """
CREATE TABLE IF NOT EXISTS families (
  id           INTEGER PRIMARY KEY,
  family       TEXT NOT NULL,
  root         TEXT NOT NULL UNIQUE,
  root_meaning TEXT NOT NULL,
  intro        TEXT NOT NULL DEFAULT '',
  source       TEXT NOT NULL DEFAULT 'seed',
  created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS words (
  id           INTEGER PRIMARY KEY,
  family_id    INTEGER NOT NULL REFERENCES families(id) ON DELETE CASCADE,
  word         TEXT NOT NULL UNIQUE,
  pos          TEXT NOT NULL DEFAULT '',
  gloss        TEXT NOT NULL,
  part         TEXT NOT NULL,
  meme         TEXT NOT NULL,
  content_type TEXT NOT NULL CHECK (content_type IN ('sentence','story','passage')),
  content_en   TEXT NOT NULL,
  content_zh   TEXT NOT NULL,
  example      TEXT NOT NULL,
  blank        TEXT NOT NULL,
  img          TEXT,
  img_zh       TEXT NOT NULL DEFAULT '',
  position     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_words_family ON words(family_id, position);

CREATE TABLE IF NOT EXISTS reviews (
  word       TEXT PRIMARY KEY REFERENCES words(word) ON DELETE CASCADE,
  stage      INTEGER NOT NULL DEFAULT 0,
  next_date  TEXT,
  wrong      INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS generation_jobs (
  id          TEXT PRIMARY KEY,
  status      TEXT NOT NULL CHECK (status IN ('pending','running','succeeded','failed')),
  kind        TEXT NOT NULL DEFAULT 'family',
  keyword     TEXT NOT NULL,
  family_id   INTEGER REFERENCES families(id) ON DELETE SET NULL,
  total       INTEGER NOT NULL DEFAULT 0,
  done        INTEGER NOT NULL DEFAULT 0,
  result_json TEXT,
  error       TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


# 2、迁移兜底
# 老库里 generation_jobs 已经建好了，CREATE TABLE IF NOT EXISTS 不会补列，只能逐列 ALTER。
JOB_COLUMNS = (("kind", "TEXT NOT NULL DEFAULT 'family'"), ("total", "INTEGER NOT NULL DEFAULT 0"),
               ("done", "INTEGER NOT NULL DEFAULT 0"), ("result_json", "TEXT"))

def _migrate(conn: sqlite3.Connection) -> None:
    have = {r["name"] for r in conn.execute("PRAGMA table_info(generation_jobs)")}
    for name, decl in JOB_COLUMNS:
        if name not in have:
            conn.execute(f"ALTER TABLE generation_jobs ADD COLUMN {name} {decl}")


# 3、每个操作新建一个连接
def connect() -> sqlite3.Connection:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


# 4、初始化
@contextmanager   #上下文管理器
def session() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# 服务启动时建表并跑迁移
def init_db() -> None:
    with session() as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)
