"""Load the seed families from seed_data.json into an empty database."""
from __future__ import annotations

import json

from . import config, repositories
from .db import session


def seed_if_empty() -> int:
    with session() as conn:
        if conn.execute("SELECT COUNT(*) FROM families").fetchone()[0]:
            return 0
        families = json.loads(config.SEED_FILE.read_text(encoding="utf-8"))
        for fam in families:
            repositories.insert_family(conn, fam, "seed")
        return len(families)
