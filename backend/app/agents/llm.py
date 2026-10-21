"""真正的底层客户端，只管“同步发请求、拿回结果化JSON、把错误说清楚”，不含任何业务/校验逻辑"""
from __future__ import annotations

import json
import re
from typing import Any

import httpx   #同步

from .. import config   #全部配置从config读，不缓存


# 统一的异常类型
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

# 把HTTP状态码翻译成“可行动的中文”
def _explain(resp: httpx.Response) -> str:
    """Turn a provider error into something the settings dialog can act on."""
    # 401、403
    if resp.status_code in (401, 403):
        return f"密钥不被接受（{resp.status_code}）：检查有没有抄错、过期，或者余额用完"
    # 404
    if resp.status_code == 404:
        return (f"接口地址或模型名不对（404）：{config.DEEPSEEK_BASE_URL} / "
                f"{config.DEEPSEEK_MODEL}")
    return f"接口返回 {resp.status_code}：{resp.text[:120]}"

# 测试模型是否联通
def ping(timeout: float = 20.0) -> tuple[bool, str]:
    """One minimal call, to prove base URL + model + key work together."""
    url = config.DEEPSEEK_BASE_URL.rstrip("/") + "/chat/completions"
    payload = {"model": config.DEEPSEEK_MODEL, "max_tokens": 1,
               "messages": [{"role": "user", "content": "ping"}]}
    try:
        resp = httpx.post(url, json=payload,
                          headers={"Authorization": f"Bearer {config.DEEPSEEK_API_KEY}"},
                          timeout=timeout)
    except httpx.HTTPError as exc:
        return False, f"连不上接口：{exc}"
    if resp.status_code >= 400:
        return False, _explain(resp)
    return True, f"接口通了，模型 {config.DEEPSEEK_MODEL} 可用"

# 发起对话，强制模型返回JSON对象
def complete_json(system: str, user: str, temperature: float = 0.8) -> Any:
    if not config.llm_ready():   #没配置就发失败信息
        raise LlmError("还没配置模型密钥，先在首页右上角的设置里填上")
    url = config.DEEPSEEK_BASE_URL.rstrip("/") + "/chat/completions"
    payload = {
        "model": config.DEEPSEEK_MODEL,
        "temperature": temperature,
        "response_format": {"type": "json_object"},   #API层面强制JSON
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
        raise LlmError(_explain(resp))
    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise LlmError("模型返回结构不完整") from exc
    return _extract_json(content)   #用正则剥离外层JSON
