"""智能体层：负责"向模型要词族内容 → 严格校验 → 修复重试 → 归一化入库"这一整条链"""
from __future__ import annotations

import re
from typing import Any, Optional

from .. import repositories
from . import image_agent, llm

CONTENT_TYPES = {"sentence", "story", "passage"}
MEME_MAX = 20
CJK = re.compile(r"[一-鿿]")
WORD_TOKEN = re.compile(r"[A-Za-z][A-Za-z'-]{1,29}")
MAX_PASTED = 120
GROUP_MIN, GROUP_MAX = 2, 8
# 词本里常混着词性标签，别把它们当成单词收进词表。
POS_NOISE = {"v", "n", "adj", "adv", "vt", "vi", "prep", "conj", "pron", "pl", "sb", "sth",
             "phr", "num", "art", "int", "abbr", "u", "c"}

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

GROUP_SYSTEM = """你是英语词族记忆卡的整理者。用户会粘一批单词（来自词本、课本单元或词表），
你要按共同词根把它们分成若干族，方便一次记一串。只输出一个 JSON 对象，不要输出解释。

{
  "groups": [
    {
      "root": "小写英文词根，如 spect",
      "rootMeaning": "这个词根的核心义，1到4个汉字",
      "why": "一句话说明这一族怎么分岔，20到40个汉字",
      "words": ["这一族的单词"]
    }
  ],
  "ungrouped": ["找不到同族伙伴的单词"]
}

硬要求：
- words 里的词必须原样来自用户给的词表，不许新造词，不许改成别的词形。
- 一个词只能出现在一个 group 里；root 的字母要能在该组每个词里原样找到。
- 每组至少 2 个词、最多 8 个词；凑不满 2 个的放进 ungrouped。
- 尽量多覆盖用户给的词，优先输出「能一起记的词最多」的组。"""


def _errors(fam: dict, expected_words: int, allowed: Optional[list[str]] = None) -> list[str]:
    """校验规则：保证单词是有效的"""
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

    if allowed:
        pool = set(allowed)
        missing = [w for w in allowed if w not in seen]
        extra = sorted(seen - pool)
        if missing:
            errs.append("少了词表里的词：" + "、".join(missing))
        if extra:
            errs.append("多出了词表外的词：" + "、".join(extra))

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

# 生成/整理一个词族，返回归一化dict：complete_json → _errors → _normalize，拿到结果先校验，再归一
def generate_family(keyword: str, words: int = 5,
                    allowed: Optional[list[str]] = None) -> dict:
    """Ask for a family on `keyword`, repair it once if validation fails, then return it.

    `allowed` pins the family to a user-supplied word list: exactly those words, no extras.
    """
    if allowed:
        expected = len(allowed)
        user = (f"请把这些词整理成一个词族，词根是「{keyword}」。words 数组必须正好 {expected} 个，"
                f"并且原样使用下面这些词，不许增删、不许改词形：\n" + "\n".join(allowed))
    else:
        expected = words
        user = (f"请以词根「{keyword}」为中心写一个 {words} 个词的词族。"
                f"如果「{keyword}」不是常见拉丁/希腊词根，就换成最接近的常用词根并在 family 里写明。"
                f"words 数组必须正好 {words} 个。")
    problems: list[str] = []
    for temperature in (0.9, 0.3):   #温度从0.9降到0.3，最多两轮。首轮高温保多样性，失败后转低温走确认。
        raw = llm.complete_json(SYSTEM, _user_with_errors(user, problems), temperature)
        if not isinstance(raw, dict):
            problems = ["返回值必须是一个 JSON 对象"]
            continue
        problems = _errors(raw, expected, allowed)   #第一轮失败就把失败原因拼进第二轮提示词里
        if not problems:   #入库前查重
            return _normalize(raw)
    raise llm.LlmError("模型两次都没写出合规的词族：" + "；".join(problems[:6]))

# 从粘贴文本抽英文单词
def parse_word_list(text: str) -> list[str]:
    """Pull the English words out of a pasted word book; separators and glosses are ignored."""
    out: list[str] = []
    seen: set[str] = set()
    for token in WORD_TOKEN.findall(text):
        word = token.strip("-'").lower()
        if len(word) < 2 or word in seen or word in POS_NOISE:
            continue
        seen.add(word)
        out.append(word)
        if len(out) >= MAX_PASTED:
            break
    return out


def _group_errors(raw: dict, pool: list[str], max_families: int) -> list[str]:
    errs: list[str] = []
    groups = raw.get("groups")
    if not isinstance(groups, list) or not groups:
        return ["groups 必须是非空数组"]
    if len(groups) > max_families:
        errs.append(f"groups 有 {len(groups)} 组，最多 {max_families} 组")
    known = set(pool)
    claimed: set[str] = set()
    for i, g in enumerate(groups):
        tag = f"groups[{i}]"
        if not isinstance(g, dict):
            errs.append(f"{tag} 不是对象")
            continue
        root = str(g.get("root", "")).lower()
        if not re.fullmatch(r"[a-z]{2,}", root):
            errs.append(f"{tag}.root 必须是2个以上小写英文字母")
        if not CJK.search(str(g.get("rootMeaning", ""))):
            errs.append(f"{tag}.rootMeaning 必须是汉字")
        items = g.get("words")
        if not isinstance(items, list) or not GROUP_MIN <= len(items) <= GROUP_MAX:
            errs.append(f"{tag}.words 必须是 {GROUP_MIN} 到 {GROUP_MAX} 个")
            continue
        for w in items:
            word = str(w).strip().lower()
            if word not in known:
                errs.append(f"{tag} 里的 {word} 不在用户词表里")
            elif word in claimed:
                errs.append(f"{word} 被分进了两个组")
            elif root and root not in word:
                errs.append(f"{tag} 里的 {word} 找不到词根 {root}")
            else:
                claimed.add(word)
    return errs


def _normalize_groups(raw: dict, pool: list[str]) -> dict:
    groups: list[dict] = []
    covered: set[str] = set()
    for g in raw["groups"]:
        words = list(dict.fromkeys(str(w).strip().lower() for w in g["words"]))
        words = [w for w in words if w in set(pool) and w not in covered]
        if len(words) < GROUP_MIN:
            continue
        covered.update(words)
        groups.append({"root": str(g["root"]).strip().lower(),
                       "rootMeaning": str(g["rootMeaning"]).strip(),
                       "why": str(g.get("why", "")).strip(),
                       "words": words})
    return {"groups": groups, "ungrouped": [w for w in pool if w not in covered],
            "total": len(pool)}

# 把粘来的词表按词根分组（只分组，不落库）
def group_words(text: str, max_families: int = 6) -> dict:
    """Split a pasted word list into root-based families, repairing once if validation fails."""
    pool = parse_word_list(text)
    if len(pool) < GROUP_MIN:
        raise llm.LlmError(f"只认出 {len(pool)} 个英文单词，至少给 {GROUP_MIN} 个")
    user = (f"下面是用户的词表，共 {len(pool)} 个词，请分成最多 {max_families} 组：\n"
            + "\n".join(pool))
    problems: list[str] = []
    for temperature in (0.4, 0.1):
        raw = llm.complete_json(GROUP_SYSTEM, _user_with_errors(user, problems), temperature)
        if not isinstance(raw, dict):
            problems = ["返回值必须是一个 JSON 对象"]
            continue
        problems = _group_errors(raw, pool, max_families)
        if not problems:
            return _normalize_groups(raw, pool)
    raise llm.LlmError("模型两次都没分出合规的词族：" + "；".join(problems[:6]))


def _user_with_errors(user: str, problems: list[str]) -> str:
    if not problems:
        return user
    return (user + "\n\n上一次输出有不合规的地方，请逐条修好，其他内容保持同等质量：\n"
            + "\n".join(f"- {p}" for p in problems[:12]))

# 手动输入词根
def store(fam: dict) -> Optional[int]:
    return repositories.add_family(fam, "agent")
