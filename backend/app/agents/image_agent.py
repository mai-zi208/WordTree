"""Agent layer: runtime illustration. No image provider is configured in this
environment, so generated families keep img=NULL and 看图解词 skips them."""
from __future__ import annotations

from typing import Optional

from .. import config


def plan_image(word_row: dict) -> Optional[str]:
    if config.IMAGE_PROVIDER == "none":
        return None
    raise NotImplementedError(
        f"IMAGE_PROVIDER={config.IMAGE_PROVIDER} 还没有接上对应的出图服务")
