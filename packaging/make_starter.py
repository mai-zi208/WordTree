"""生成打进包里的脱敏起始词库：只留 families 和 words，私人数据清空。

不能直接把 backend/data/wordmemo.db 拷进包里 —— 那里面有你的复习记录，
别人拿到手第一屏就是"5/5 已学"，而且永远等不到学新词的那一轮。
"""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "backend" / "data" / "wordmemo.db"
OUT = HERE / "starter" / "wordmemo.db"

# 删掉的就是"私人"那部分；词库正文（族与词）和已生成的配图是内容，不是隐私，照带。
PRIVATE_TABLES = ("reviews", "generation_jobs")


def main() -> None:
    if not SRC.is_file():
        raise SystemExit(f"找不到本机词库 {SRC}，先把开发环境跑起来让它建出来")

    # 先让源库把 WAL 里的内容落回主文件，否则拷走的可能是个缺最近写入的半份库。
    src = sqlite3.connect(SRC)
    src.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    src.close()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.unlink(missing_ok=True)
    shutil.copy2(SRC, OUT)

    with sqlite3.connect(OUT) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        for table in PRIVATE_TABLES:
            conn.execute(f"DELETE FROM {table}")

    conn = sqlite3.connect(OUT)
    conn.isolation_level = None          # VACUUM 不能待在事务里
    conn.execute("VACUUM")
    left = conn.execute("select (select count(*) from families), (select count(*) from words),"
                        " (select count(*) from reviews), (select count(*) from generation_jobs)").fetchone()
    conn.close()
    print(f"脱敏起始库 {OUT}：{left[0]} 族 {left[1]} 词，reviews={left[2]} jobs={left[3]}")


if __name__ == "__main__":
    main()
