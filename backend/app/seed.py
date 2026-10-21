"""将 seed_data.json 中的种子家族加载到一个空数据库中。"""
from __future__ import annotations

import json

from . import config, repositories
from .db import session

# 首启动初始化，让首页点开就有词族，repositories来插入，它只负责判断要不要插入
def seed_if_empty() -> int:
    with session() as conn:
        if conn.execute("SELECT COUNT(*) FROM families").fetchone()[0]:
            return 0
        families = json.loads(config.SEED_FILE.read_text(encoding="utf-8"))
        for fam in families:
            repositories.insert_family(conn, fam, "seed")
        return len(families)
