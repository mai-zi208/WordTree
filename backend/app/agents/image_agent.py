"""智能体层：负责出图，但现在没有功能"""
from __future__ import annotations

from typing import Optional

from .. import config


def plan_image(word_row: dict) -> Optional[str]:
    if config.IMAGE_PROVIDER == "none":
        return None
    raise NotImplementedError(
        f"IMAGE_PROVIDER={config.IMAGE_PROVIDER} 还没有接上对应的出图服务")
