"""设置面板的后端接口：配置模型，返回连接结果"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import config, schemas
from ..agents import llm

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _current() -> dict:
    """返回配置值+是否已配key+打码key"""
    return {"baseUrl": config.DEEPSEEK_BASE_URL, "model": config.DEEPSEEK_MODEL,
            "imageProvider": config.IMAGE_PROVIDER, "imageModel": config.IMAGE_MODEL,
            "imageReady": config.image_ready(), "configured": config.llm_ready(),
            "keyHint": config.masked_key()}

# 回显当前模型配置
@router.get("")
def read() -> dict:
    return _current()

# 写入新模型配置，可选顺带ping验证
@router.put("")
def write(body: schemas.SettingsRequest) -> dict:
    updates = {k: v for k, v in body.as_env().items() if v is not None}
    try:
        config.write_env(updates)
    except (ValueError, OSError) as exc:
        raise HTTPException(400, f"写 {config.ENV_FILE} 失败：{exc}") from exc
    out = _current()
    if body.verify:
        if config.llm_ready():
            ok, message = llm.ping()
        else:
            ok, message = False, "密钥是空的，没法测"
        out["check"] = {"ok": ok, "message": message}
    return out
