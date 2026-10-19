"""Runtime configuration: process env is the base, backend/.env is the user-editable layer."""

from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
ASSETS_DIR = PROJECT_ROOT / "assets"
DIST_DIR = PROJECT_ROOT / "web" / "dist"
SEED_FILE = Path(__file__).resolve().parent / "seed_data.json"
ENV_FILE = BACKEND_DIR / ".env"

# 启动时的进程环境快照。.env 覆盖它；有了快照，reload() 才不会把上一轮 .env 的值误当成进程环境。
_BASE_ENV = dict(os.environ)

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

# 设置页可改的键；顺序即 .env 里的书写顺序。
EDITABLE_KEYS = ("DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL", "DEEPSEEK_API_KEY",
                 "WORDMEMO_IMAGE_PROVIDER")


def parse_env_file(path: Path = ENV_FILE) -> dict[str, str]:
    """Read a flat KEY=VALUE file. Comments, blank lines and quotes are tolerated."""
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def effective_env() -> dict[str, str]:
    return {**_BASE_ENV, **parse_env_file()}


def reload() -> None:
    """Re-read env + .env into the settings the LLM layer reads at call time."""
    global DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, LLM_TIMEOUT_S, IMAGE_PROVIDER
    env = effective_env()
    DEEPSEEK_API_KEY = env.get("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = env.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL = env.get("DEEPSEEK_MODEL", "deepseek-chat")
    LLM_TIMEOUT_S = float(env.get("WORDMEMO_LLM_TIMEOUT", "90"))
    IMAGE_PROVIDER = env.get("WORDMEMO_IMAGE_PROVIDER", "none")


def write_env(updates: dict[str, str]) -> None:
    """Merge updates into backend/.env and reload. Empty value removes the key."""
    current = parse_env_file()
    for key, value in updates.items():
        value = str(value).strip()
        if "\n" in value or "\r" in value:
            raise ValueError(f"{key} 里不能有换行")
        if value:
            current[key] = value
        else:
            current.pop(key, None)
    lines = [f"{k}={current[k]}" for k in EDITABLE_KEYS if k in current]
    lines += [f"{k}={v}" for k, v in current.items() if k not in EDITABLE_KEYS]
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = ENV_FILE.parent / (ENV_FILE.name + ".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(tmp, ENV_FILE)
    reload()


def masked_key() -> str:
    """Last 4 chars only, for the settings UI. Never returns the key itself."""
    if not DEEPSEEK_API_KEY:
        return ""
    tail = DEEPSEEK_API_KEY[-4:]
    return f"****{tail}" if len(DEEPSEEK_API_KEY) > 4 else "****"


def llm_ready() -> bool:
    return bool(DEEPSEEK_API_KEY)


reload()
