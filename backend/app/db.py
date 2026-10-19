"""SQLite access: one file, no ORM, WAL so the dev server can read while writing."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from . import config

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
  id         TEXT PRIMARY KEY,
  status     TEXT NOT NULL CHECK (status IN ('pending','running','succeeded','failed')),
  keyword    TEXT NOT NULL,
  family_id  INTEGER REFERENCES families(id) ON DELETE SET NULL,
  error      TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def connect() -> sqlite3.Connection:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
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


def init_db() -> None:
    with session() as conn:
        conn.executescript(SCHEMA)
