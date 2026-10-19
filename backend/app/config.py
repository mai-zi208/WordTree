"""Runtime configuration, resolved once from the environment."""

from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
ASSETS_DIR = PROJECT_ROOT / "assets"
DIST_DIR = PROJECT_ROOT / "web" / "dist"
SEED_FILE = Path(__file__).resolve().parent / "seed_data.json"

DB_PATH = Path(os.getenv("WORDMEMO_DB", DATA_DIR / "wordmemo.db"))
HOST = os.getenv("WORDMEMO_HOST", "127.0.0.1")
PORT = int(os.getenv("WORDMEMO_PORT", "8000"))

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
LLM_TIMEOUT_S = float(os.getenv("WORDMEMO_LLM_TIMEOUT", "90"))

# No image-provider key is present in this environment, so runtime illustration
# generation stays disabled and families are stored with img=NULL.
IMAGE_PROVIDER = os.getenv("WORDMEMO_IMAGE_PROVIDER", "none")

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "WORDMEMO_CORS",
        "http://127.0.0.1:5273,http://localhost:5273,"
        "http://127.0.0.1:5274,http://localhost:5274",
    ).split(",")
    if o.strip()
]


def llm_ready() -> bool:
    return bool(DEEPSEEK_API_KEY)
