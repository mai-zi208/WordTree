"""智能体层：出图。把词的联想画面交给生图模型，下载回本地存好，给出库里的相对路径。"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import httpx

from .. import config

# 接口只回一个几天就过期的 OSS 链接，所以必须把图片下载下来自己存，存到 /media 挂载位。
URL_PREFIX = "media"
# 尺寸要用星号写，写成 1024x1024 会被拒；不给这个参数的话默认出 1024x1536 的竖图。
SIZE = "1024*1024"
STYLE = ("手绘水彩简笔画：淡彩上色，线条松弛，大片留白，一张图只画一件事，"
         "不要写字、不要字母、不要水印、不要边框。")
MAGIC = ((b"\x89PNG", "png"), (b"\xff\xd8", "jpg"), (b"RIFF", "webp"))
SAFE_NAME = re.compile(r"[^a-z0-9_-]+")


class ImageError(RuntimeError):
    pass


def build_prompt(word_row: dict) -> str:
    """联想画面（meme）就是要画的内容，单词和释义只给模型一点上下文。"""
    return (f"{word_row.get('meme', '')}。画面主角是「{word_row['word']}」"
            f"（{word_row.get('gloss', '')}）。{STYLE}")


def _explain(resp: httpx.Response) -> str:
    """把接口错误翻成设置页能照着改的中文，跟 llm._explain 一个路子。"""
    try:
        detail = resp.json()
    except ValueError:
        detail = {}
    err = detail.get("error")
    message = (detail.get("message") or (err.get("message") if isinstance(err, dict) else err)
               or resp.text[:160])
    # 模型名写错时接口也回 404，但正文写着 Model not exist，先看正文才不会把人往地址上引。
    if "not exist" in str(message).lower():
        return f"生图模型 {config.IMAGE_MODEL} 在这儿不存在，去设置里换个 /models 里真有的名字"
    if resp.status_code in (401, 403):
        return f"密钥不被接受（{resp.status_code}）：生图跟聊天共用同一把密钥，检查有没有过期或欠费"
    if resp.status_code == 404:
        return (f"生图接口不通（404）：{config.image_endpoint()}，"
                f"这个中转站可能压根没有生图接口")
    return f"生图接口返回 {resp.status_code}：{message}"


def _pick_url(payload: dict) -> Optional[str]:
    """从多模态返回里挑出图片链接，几种模型把它放的位置不完全一样。"""
    for choice in (payload.get("output") or {}).get("choices") or []:
        for item in (choice.get("message") or {}).get("content") or []:
            if isinstance(item, dict) and item.get("image"):
                return str(item["image"])
    return None


def _save(word: str, raw: bytes) -> str:
    """按文件头认出格式再落盘，返回库里存的相对路径（序列化时会补成 /media/xxx.png）。"""
    ext = next((ext for magic, ext in MAGIC if raw.startswith(magic)), "")
    if not ext:
        raise ImageError("接口给的不是图片，前几个字节认不出来")
    config.IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    name = SAFE_NAME.sub("-", word.lower()).strip("-") or "word"
    path = Path(config.IMAGES_DIR) / f"{name}.{ext}"
    path.write_bytes(raw)
    return f"{URL_PREFIX}/{path.name}"


def generate(word_row: dict) -> tuple[str, str]:
    """Draw one illustration for a word and store it locally.

    Returns (relative path for the words.img column, Chinese caption for words.img_zh).
    """
    if not config.image_ready():
        raise ImageError("还没开生图：去设置里把出图服务打成 dashscope，密钥跟聊天共用一把")
    payload = {"model": config.IMAGE_MODEL,
               "input": {"messages": [{"role": "user",
                                       "content": [{"text": build_prompt(word_row)}]}]},
               "parameters": {"size": SIZE}}
    try:
        resp = httpx.post(config.image_endpoint(), json=payload,
                          headers={"Authorization": f"Bearer {config.DEEPSEEK_API_KEY}"},
                          timeout=config.IMAGE_TIMEOUT_S)
    except httpx.HTTPError as exc:
        raise ImageError(f"调用生图接口失败：{exc}") from exc
    if resp.status_code >= 400:
        raise ImageError(_explain(resp))
    url = _pick_url(resp.json() if resp.content else {})
    if not url:
        raise ImageError("接口通了但没给图片链接，换个生图模型再试")
    try:
        shot = httpx.get(url, timeout=config.IMAGE_TIMEOUT_S)
        shot.raise_for_status()
    except httpx.HTTPError as exc:
        raise ImageError(f"图片下载不下来：{exc}") from exc
    return _save(word_row["word"], shot.content), str(word_row.get("meme", "")).strip()
