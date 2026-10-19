"""Agent layer: ask the model for a new word family, validate it, store it."""
from __future__ import annotations

import re
from typing import Any, Optional

from .. import repositories
from . import image_agent, llm

CONTENT_TYPES = {"sentence", "story", "passage"}
MEME_MAX = 20
CJK = re.compile(r"[一-鿿]")

SYSTEM = """你是英语词族记忆卡的内容作者，为一个中国大学生写「用联想记住单词」的材料。
只输出一个 JSON 对象，不要输出解释。字段名必须严格照下面的结构，全部用 json。

{
  "family": "词族名，等于词根",
  "root": "英文词根，小写字母",
  "rootMeaning": "这个词根的核心义，1到4个汉字",
  "intro": "一句话介绍这个词族怎么分岔，20到40个汉字",
  "words": [
    {
      "word": "英文单词",
      "pos": "词性，如 v. n. a.",
      "gloss": "中文释义，2到6个汉字",
      "part": "构词拆解，形如 in- 往里 + spect 看，必须包含词根本身",
      "meme": "联想画面，不超过20个汉字，用谐音或沙雕画面，不要讲道理",
      "content": {"type": "sentence 或 story 或 passage", "en": "英文原文", "zh": "中文翻译"},
      "example": "一句4到9个英文单词的短句，里面必须出现 blank 那个词形",
      "blank": "example 里实际出现的那个词形，可以是变形，如 inspected"
    }
  ]
}

内容形式的分工：抽象概念用 story（1到2句英文）；带人物张力的情感判断词用 passage（2句，
有留白）；日常词语用 sentence（1句）。三种形式混着安排，一族里不要全是一种。
content.en 只能写英文，一句中文都不要出现；中文全部放在 content.zh。
meme 只写画面，不写词义解释；meme 不超过20个汉字是硬要求。
每个单词必须由这个词根派生，词根字母要能在单词里原样找到。"""


def _errors(fam: dict, expected_words: int) -> list[str]:
    errs: list[str] = []
    root = str(fam.get("root", "")).lower()
    if not re.fullmatch(r"[a-z]{2,}", root):
        errs.append("root 必须是2个以上小写英文字母")
    if not CJK.search(str(fam.get("rootMeaning", ""))):
        errs.append("rootMeaning 必须是汉字")
    if len(str(fam.get("intro", ""))) < 8:
        errs.append("intro 太短")
    words = fam.get("words")
    if not isinstance(words, list) or len(words) != expected_words:
        errs.append(f"words 必须是 {expected_words} 个")
        return errs

    seen: set[str] = set()
    for i, w in enumerate(words):
        tag = f"words[{i}]"
        if not isinstance(w, dict):
            errs.append(f"{tag} 不是对象")
            continue
        word = str(w.get("word", "")).lower()
        if not re.fullmatch(r"[a-z]{2,24}", word):
            errs.append(f"{tag}.word 必须是纯英文字母")
            continue
        if word in seen:
            errs.append(f"{tag}.word 在本族里重复：{word}")
            continue
        seen.add(word)
        if root and root not in word:
            errs.append(f"{tag}.word {word} 里找不到词根 {root}")
        if not CJK.search(str(w.get("gloss", ""))):
            errs.append(f"{tag}.gloss 必须是中文")
        meme = str(w.get("meme", ""))
        if len(meme) > MEME_MAX:
            errs.append(f"{tag}.meme 有 {len(meme)} 个字符，不能超过 {MEME_MAX}")
        if not CJK.search(meme):
            errs.append(f"{tag}.meme 必须是中文画面")
        if root not in str(w.get("part", "")).lower():
            errs.append(f"{tag}.part 里必须出现词根 {root}")
        content = w.get("content") or {}
        if content.get("type") not in CONTENT_TYPES:
            errs.append(f"{tag}.content.type 只能是 sentence/story/passage")
        en = str(content.get("en", ""))
        if len(en.split()) < 4:
            errs.append(f"{tag}.content.en 太短")
        if CJK.search(en):
            errs.append(f"{tag}.content.en 里混进了中文，中文只能写在 zh")
        if not CJK.search(str(content.get("zh", ""))):
            errs.append(f"{tag}.content.zh 必须是中文")
        example, blank = str(w.get("example", "")), str(w.get("blank", "")).lower()
        if not example or len(example.split()) < 4 or len(example.split()) > 9:
            errs.append(f"{tag}.example 需要 4 到 9 个英文单词")
        if not blank:
            errs.append(f"{tag}.blank 不能为空")
        elif not re.search(r"\b" + re.escape(blank) + r"\b", example, re.I):
            errs.append(f"{tag}.blank「{blank}」没有原样出现在 example 里")
        elif not blank.startswith(word[:-2]):
            errs.append(f"{tag}.blank「{blank}」不是 {word} 的变形")

    if errs:
        return errs
    known = {x["word"] for x in repositories.all_words()}
    for word in seen:
        if word in known:
            errs.append(f"{word} 已经在词库里，换一个")
    return errs


def _normalize(fam: dict) -> dict:
    root = str(fam["root"]).lower()
    out = {
        "family": str(fam.get("family") or root).lower(),
        "root": root,
        "rootMeaning": str(fam["rootMeaning"]).strip(),
        "intro": str(fam.get("intro", "")).strip(),
        "words": [],
    }
    for i, w in enumerate(fam["words"]):
        content = w["content"]
        img = image_agent.plan_image(w)
        out["words"].append({
            "word": str(w["word"]).lower(),
            "pos": str(w.get("pos", "")).strip(),
            "gloss": str(w["gloss"]).strip(),
            "part": str(w["part"]).strip(),
            "meme": str(w["meme"]).strip(),
            "content": {"type": content["type"], "en": str(content["en"]).strip(),
                        "zh": str(content["zh"]).strip()},
            "example": str(w["example"]).strip(),
            "blank": str(w["blank"]).strip(),
            "img": img,
            "img_zh": "",
        })
    return out


def generate_family(keyword: str, words: int = 5) -> dict:
    """Ask for a family on `keyword`, repair it once if validation fails, then return it."""
    user = (f"请以词根「{keyword}」为中心写一个 {words} 个词的词族。"
            f"如果「{keyword}」不是常见拉丁/希腊词根，就换成最接近的常用词根并在 family 里写明。"
            f"words 数组必须正好 {words} 个。")
    problems: list[str] = []
    for temperature in (0.9, 0.3):
        raw = llm.complete_json(SYSTEM, _user_with_errors(user, problems), temperature)
        if not isinstance(raw, dict):
            problems = ["返回值必须是一个 JSON 对象"]
            continue
        problems = _errors(raw, words)
        if not problems:
            return _normalize(raw)
    raise llm.LlmError("模型两次都没写出合规的词族：" + "；".join(problems[:6]))


def _user_with_errors(user: str, problems: list[str]) -> str:
    if not problems:
        return user
    return (user + "\n\n上一次输出有不合规的地方，请逐条修好，其他内容保持同等质量：\n"
            + "\n".join(f"- {p}" for p in problems[:12]))


def store(fam: dict) -> Optional[int]:
    return repositories.add_family(fam, "agent")
