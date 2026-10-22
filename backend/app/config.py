"""运行时配置：process env 是基础，backend/.env 是用户可编辑的层级。"""

from __future__ import annotations

import os
from pathlib import Path

# 1、设置路径常量
BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"   # SQLite数据库
IMAGES_DIR = DATA_DIR / "images"   # 智能体生成的插图，跟数据库一起被 git 忽略
ASSETS_DIR = PROJECT_ROOT / "assets"   # 图片资源
DIST_DIR = PROJECT_ROOT / "web" / "dist"   # 前端构建产物
SEED_FILE = Path(__file__).resolve().parent / "seed_data.json"   # 种子数据
ENV_FILE = BACKEND_DIR / ".env"

# 启动时的进程环境快照。.env 覆盖它；有了快照，reload() 才不会把上一轮 .env 的值误当成进程环境。
_BASE_ENV = dict(os.environ)


# 2、从环境变量读取配置项
DB_PATH = Path(os.getenv("WORDMEMO_DB", DATA_DIR / "wordmemo.db"))
HOST = os.getenv("WORDMEMO_HOST", "127.0.0.1")
PORT = int(os.getenv("WORDMEMO_PORT", "8000"))

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
LLM_TIMEOUT_S = float(os.getenv("WORDMEMO_LLM_TIMEOUT", "90"))

# 生图：dashscope 走千问/万相那一系的多模态接口，跟聊天共用同一把密钥和同一个域名。
# none 表示不出图（比如密钥是 DeepSeek 的，它没有生图接口）。
IMAGE_PROVIDER = os.getenv("WORDMEMO_IMAGE_PROVIDER", "none")
IMAGE_MODEL = os.getenv("WORDMEMO_IMAGE_MODEL", "z-image-turbo")
# 出图比聊天慢得多：turbo 一秒级，qwen-image-3.0 实测要一分钟，所以超时单给一个值。
IMAGE_TIMEOUT_S = float(os.getenv("WORDMEMO_IMAGE_TIMEOUT", "180"))

# 前端端口
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
                 "WORDMEMO_IMAGE_PROVIDER", "WORDMEMO_IMAGE_MODEL")


# 3、读写与热更新函数
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

# 合并环境变量
def effective_env() -> dict[str, str]:
    return {**_BASE_ENV, **parse_env_file()}

# LLM参数保持后不刷新
def reload() -> None:
    """Re-read env + .env into the settings the LLM layer reads at call time."""
    global DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, LLM_TIMEOUT_S
    global IMAGE_PROVIDER, IMAGE_MODEL, IMAGE_TIMEOUT_S
    env = effective_env()
    DEEPSEEK_API_KEY = env.get("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL = env.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL = env.get("DEEPSEEK_MODEL", "deepseek-chat")
    LLM_TIMEOUT_S = float(env.get("WORDMEMO_LLM_TIMEOUT", "90"))
    IMAGE_PROVIDER = env.get("WORDMEMO_IMAGE_PROVIDER", "none")
    IMAGE_MODEL = env.get("WORDMEMO_IMAGE_MODEL", "z-image-turbo")
    IMAGE_TIMEOUT_S = float(env.get("WORDMEMO_IMAGE_TIMEOUT", "180"))

# 环境变量写回.env
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


# 4、辅助查询
def masked_key() -> str:
    """Last 4 chars only, for the settings UI. Never returns the key itself."""
    if not DEEPSEEK_API_KEY:
        return ""
    tail = DEEPSEEK_API_KEY[-4:]
    return f"****{tail}" if len(DEEPSEEK_API_KEY) > 4 else "****"

# 是否配置API Key
def llm_ready() -> bool:
    return bool(DEEPSEEK_API_KEY)


def image_ready() -> bool:
    """生图和聊天共用一把密钥，所以只看开关开没开、密钥有没有。"""
    return IMAGE_PROVIDER == "dashscope" and bool(DEEPSEEK_API_KEY)


def image_endpoint() -> str:
    """生图走原生 DashScope 路径，不是 /chat/completions，先把兼容模式的尾巴剪掉。"""
    base = DEEPSEEK_BASE_URL.rstrip("/")
    for suffix in ("/compatible-mode/v1", "/v1"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    return base + "/api/v1/services/aigc/multimodal-generation/generation"


reload()
