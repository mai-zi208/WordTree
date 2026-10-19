"""DeepSeek chat client (OpenAI-compatible). Synchronous: callers run it off-loop."""
from __future__ import annotations

import json
import re
from typing import Any

import httpx

from .. import config


class LlmError(RuntimeError):
    pass


def _extract_json(text: str) -> Any:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.+?)\s*```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start = min([i for i in (text.find("{"), text.find("[")) if i >= 0] or [0])
    text = text[start:]
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise LlmError(f"模型没有返回合法 JSON：{exc}") from exc


def complete_json(system: str, user: str, temperature: float = 0.8) -> Any:
    if not config.llm_ready():
        raise LlmError("没有配置 DEEPSEEK_API_KEY，无法生成词族")
    url = config.DEEPSEEK_BASE_URL.rstrip("/") + "/chat/completions"
    payload = {
        "model": config.DEEPSEEK_MODEL,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
    }
    try:
        resp = httpx.post(url, json=payload,
                          headers={"Authorization": f"Bearer {config.DEEPSEEK_API_KEY}"},
                          timeout=config.LLM_TIMEOUT_S)
    except httpx.HTTPError as exc:
        raise LlmError(f"调用模型失败：{exc}") from exc
    if resp.status_code >= 400:
        raise LlmError(f"模型返回 {resp.status_code}：{resp.text[:200]}")
    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise LlmError("模型返回结构不完整") from exc
    return _extract_json(content)
