"""智能体层：负责"向模型要词族内容 → 严格校验 → 修复重试 → 归一化入库"这一整条链"""
from __future__ import annotations

import re
from typing import Any, Optional

from .. import repositories
from . import llm

CONTENT_TYPES = {"sentence", "story", "passage"}
MEME_MAX = 20
CJK = re.compile(r"[一-鿿]")
WORD_TOKEN = re.compile(r"[A-Za-z][A-Za-z'-]{1,29}")
MAX_PASTED = 120
GROUP_MIN, GROUP_MAX = 2, 8
# 词本里常混着词性标签，别把它们当成单词收进词表。
POS_NOISE = {"v", "n", "adj", "adv", "vt", "vi", "prep", "conj", "pron", "pl", "sb", "sth",
             "phr", "num", "art", "int", "abbr", "u", "c"}

# 每个词的字段全摊平：嵌套一层 content 对象时 qwen-max 会把 en/zh 漏到外面、
# 把最后一个词吞掉，摊平之后它才能稳定写满整族。存库时再由 _normalize 拼回 content。
_SYSTEM_HEAD = """你是英语词族记忆卡的内容作者，为一个中国大学生写「用联想记住单词」的材料。
只输出一个 JSON 对象，不要输出解释。字段名必须严格照下面的结构，全部用 json。

{
  "family": "词族名，等于词根",
  "root": "英文词根，小写字母",
  "rootMeaning": "这个词根的核心义，1到4个汉字",
  "intro": "一句话介绍这个词族怎么分岔，20到40个汉字",
  "words": [
    {"word": "英文单词", "pos": "词性，如 v. n. a.", "gloss": "中文释义，2到6个汉字",
     "part": "构词拆解，形如 in- 往里 + spect 看，必须包含词根本身",
     "meme": "联想画面，不超过20个汉字，用谐音或沙雕画面，不要讲道理",
     "ctype": "sentence 或 story 或 passage", "cen": "英文原文", "czh": "中文翻译",
     "example": "一句4到12个英文单词的短句，里面必须出现 blank 那个词形",
     "blank": "example 里实际出现的那个词形，可以是变形，如 inspected"}
  ]
}

words 里每个元素都必须是对象，上面这些字段一个都不能少、不能挪到别处。
内容形式的分工：抽象概念用 story（1到2句英文）；带人物张力的情感判断词用 passage（2句，
有留白）；日常词语用 sentence（1句）。三种形式混着安排，一族里不要全是一种。
cen 只能写英文，一句中文都不要出现；中文全部放在 czh。
meme 只写画面，不写词义解释；meme 不超过20个汉字是硬要求。
"""

SYSTEM = _SYSTEM_HEAD + "每个单词必须由这个词根派生，词根字母要能在单词里原样找到。"

# 主题族：几个串不起词根的词，靠共同话题凑成一族。字段名跟词根族一样，
# 只是 root 换成主题标签，part 写各词自己的构词拆解。
THEME_SYSTEM = _SYSTEM_HEAD + """这些词不共享词根，靠一个共同主题串起来记：
- root 填这一族的主题标签，小写英文单词，如 kitchen、money、feeling。
- rootMeaning 填主题的中文名，family 跟 root 一样。
- intro 说明这几个词凭什么放在一起记。
- part 写这个词自己的构词拆解（前缀 + 词根 + 后缀，形如 re- 再 + luct 挣扎），
  不要求出现主题标签。apple 这种拆不开的基础词，就写它的词源或谐音来历
  （形如 谐音「阿婆」，阿婆递来一个苹果），别把单词和中文释义再抄一遍。
- meme 要把这个词和主题画面绑在一起，让整族读下来是同一个场景。"""

GROUP_SYSTEM = """你是英语词族记忆卡的整理者。用户会粘一批单词（来自词本、课本单元或词表），
你要按共同词根把它们分成若干族，方便一次记一串。只输出一个 JSON 对象，不要输出解释。

{
  "groups": [
    {
      "root": "小写英文词根，如 spect",
      "rootMeaning": "这个词根的核心义，1到4个汉字",
      "why": "一句话说明这一族怎么分岔，20到40个汉字",
      "words": "这一族的单词，用英文逗号隔开，如 inspect, respect"
    }
  ],
  "ungrouped": "找不到同族伙伴的单词，同样用英文逗号隔开"
}

硬要求：
- words 和 ungrouped 都是**一个字符串**，不是数组，词与词之间用英文逗号隔开。
- 词必须原样来自用户给的词表，不许新造词，不许改成别的词形，不许带上中文释义。
- 一个词只能出现在一个 group 里；root 的字母要能在该组每个词里原样找到。
- 每组至少 2 个词、最多 8 个词；凑不满 2 个的放进 ungrouped。
- 用户给的每个词都要有交代：要么在某个 group 的 words 里，要么在 ungrouped 里。
- 尽量多覆盖用户给的词，优先输出「能一起记的词最多」的组。"""

THEME_GROUP_SYSTEM = """你是英语单词记忆卡的整理者。下面这些词凑不出共同词根，
你要按「能帮着一起记的联系」把它们分成几组：同一个场景、同一类事物、同一种情绪，
或者能串进同一个画面的都行。只输出一个 JSON 对象，不要输出解释。

{
  "groups": [
    {
      "root": "这一组的主题标签，小写英文单词，如 kitchen",
      "rootMeaning": "这个主题的中文名，1到4个汉字",
      "why": "一句话说明这几个词凭什么放一起记，20到40个汉字",
      "words": "这一组的单词，用英文逗号隔开，如 apple, grape"
    }
  ],
  "ungrouped": "实在跟谁都搭不上的单词，同样用英文逗号隔开"
}

硬要求：
- words 和 ungrouped 都是**一个字符串**，不是数组，词与词之间用英文逗号隔开。
- 词必须原样来自下面给的词表，不许新造词，不许改成别的词形，不许带上中文释义。
- 一个词只能出现在一个 group 里。
- 每组至少 2 个词、最多 8 个词；凑不满 2 个的放进 ungrouped。
- 给的每个词都要有交代：要么在某个 group 的 words 里，要么在 ungrouped 里。
- 联系要真能帮上记忆，别为了凑数把不相干的词硬塞一组，宁可放进 ungrouped。"""


def _content(w: dict) -> dict:
    """读一个词的正文。提示词要的是摊平的 ctype/cen/czh，模型偶尔还是写成嵌套的 content。"""
    if "ctype" in w or "cen" in w:
        return {"type": w.get("ctype"), "en": w.get("cen"), "zh": w.get("czh")}
    return w.get("content") or {}


def _errors(fam: dict, expected_words: int, allowed: Optional[list[str]] = None,
            kind: str = "root", extra_known: Optional[set[str]] = None) -> list[str]:
    """校验规则：保证单词是有效的。主题族不查「词根是单词的子串」，改查 part 是不是写了拆解。"""
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
        if kind != "theme" and root and root not in word:
            errs.append(f"{tag}.word {word} 里找不到词根 {root}")
        if not CJK.search(str(w.get("gloss", ""))):
            errs.append(f"{tag}.gloss 必须是中文")
        meme = str(w.get("meme", ""))
        if len(meme) > MEME_MAX:
            errs.append(f"{tag}.meme 有 {len(meme)} 个字符，不能超过 {MEME_MAX}")
        if not CJK.search(meme):
            errs.append(f"{tag}.meme 必须是中文画面")
        part = str(w.get("part", "")).strip()
        if kind == "theme":
            if len(part) < 4:
                errs.append(f"{tag}.part 要写出这个词自己的构词拆解")
        elif root not in part.lower():
            errs.append(f"{tag}.part 里必须出现词根 {root}")
        content = _content(w)
        if content.get("type") not in CONTENT_TYPES:
            errs.append(f"{tag}.ctype 只能是 sentence/story/passage")
        en = str(content.get("en", ""))
        if len(en.split()) < 4:
            errs.append(f"{tag}.cen 太短")
        if CJK.search(en):
            errs.append(f"{tag}.cen 里混进了中文，中文只能写在 czh")
        if not CJK.search(str(content.get("zh", ""))):
            errs.append(f"{tag}.czh 必须是中文")
        example, blank = str(w.get("example", "")), str(w.get("blank", "")).lower()
        if not 4 <= len(example.split()) <= 12:
            errs.append(f"{tag}.example 有 {len(example.split())} 个英文单词，需要 4 到 12 个")
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
    # 同一次批量里前面几族还没入库，所以除了词库还要看已经生成好的那些词。
    known = {x["word"] for x in repositories.all_words()} | (extra_known or set())
    for word in seen:
        if word in known:
            errs.append(f"{word} 已经在词库里，换一个")
    return errs


def _normalize(fam: dict, kind: str = "root") -> dict:
    root = str(fam["root"]).lower()
    out = {
        "family": str(fam.get("family") or root).lower(),
        "root": root,
        "rootMeaning": str(fam["rootMeaning"]).strip(),
        "intro": str(fam.get("intro", "")).strip(),
        "kind": kind,
        "words": [],
    }
    for i, w in enumerate(fam["words"]):
        content = _content(w)
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
            # 图不在这儿出：一族五个词就是五张图，等用户看过内容再按需点「配图」。
            "img": None,
            "img_zh": "",
        })
    return out

# 生成/整理一个词族，返回归一化dict：complete_json → _errors → _normalize，拿到结果先校验，再归一
def generate_family(keyword: str, words: int = 5, allowed: Optional[list[str]] = None,
                    kind: str = "root", meaning: str = "",
                    extra_known: Optional[set[str]] = None) -> dict:
    """Ask for a family on `keyword`, repair it once if validation fails, then return it.

    `allowed` pins the family to a user-supplied word list: exactly those words, no extras.
    `kind='theme'` asks for a topic-linked group instead of a root family.
    """
    theme = kind == "theme"
    name = f"主题「{keyword}」" + (f"（{meaning}）" if meaning else "") if theme \
        else f"词根「{keyword}」" + (f"（{meaning}）" if meaning else "")
    if allowed:
        expected = len(allowed)
        user = (f"请把这些词整理成一个{'主题记忆卡组' if theme else '词族'}，{name}。"
                f"words 数组必须正好 {expected} 个，"
                f"并且原样使用下面这些词，不许增删、不许改词形：\n" + "\n".join(allowed))
    else:
        expected = words
        user = (f"请以{name}为中心写一个 {words} 个词的"
                f"{'主题记忆卡组' if theme else '词族'}。"
                + ("" if theme else
                   # 自己挑词时最容易踩的坑：挑中拼写变过形的派生词（aqua → aqueous），
                   # 词根在词里找不到，用户就看不出规律，所以先把这条说死。
                   f"如果「{keyword}」不是常见拉丁/希腊词根，就换成最接近的常用词根并在 family 里写明。"
                   f"挑的每个词都必须原样包含「{keyword}」这一串字母；"
                   f"词根在里面变了形的（少字母、换元音）一律不要，换成原样包含它的常见词。")
                + f"words 数组必须正好 {words} 个。")
    problems: list[str] = []
    for temperature in (0.9, 0.3):   #温度从0.9降到0.3，最多两轮。首轮高温保多样性，失败后转低温走确认。
        system = THEME_SYSTEM if theme else SYSTEM
        raw = llm.complete_json(system, _user_with_errors(user, problems), temperature)
        if not isinstance(raw, dict):
            problems = ["返回值必须是一个 JSON 对象"]
            continue
        problems = _errors(raw, expected, allowed, kind, extra_known)   #失败原因拼进第二轮提示词
        if not problems:   #入库前查重
            return _normalize(raw, kind)
    raise llm.LlmError("模型两次都没写出合规的词族：" + "；".join(problems[:6]))


def generate_group(group: dict, extra_known: Optional[set[str]] = None) -> dict:
    """生成一个已经分好的组。组里没给词（用户只输入了一个词根）就让模型自己挑常见词。"""
    words = [w for w in group.get("words") or [] if w]
    if not words:
        return generate_family(group["root"], kind=group.get("kind", "root"),
                               meaning=group.get("rootMeaning", ""), extra_known=extra_known)
    return generate_family(group["root"], allowed=words, kind=group.get("kind", "root"),
                           meaning=group.get("rootMeaning", ""), extra_known=extra_known)

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


def _word_list(value: Any) -> Optional[list[str]]:
    """词表可能是一个字符串（"a, b"）也可能是数组，两种都收下；都不是就返回 None。"""
    if isinstance(value, str):
        return [w for w in re.split(r"[,，;；\s]+", value) if w]
    if isinstance(value, list):
        return [str(w) for w in value]
    return None


def _group_errors(raw: dict, pool: list[str], max_families: int, kind: str = "root",
                  force: bool = False) -> list[str]:
    """挑模型能改的毛病。词数不对不算毛病（丢组就行），漏词和写坏结构要让它重来一次。"""
    errs: list[str] = []
    groups = raw.get("groups")
    if not isinstance(groups, list):
        return ["groups 必须是数组"]
    if force and not groups:
        errs.append("这次必须至少分出一组，一个组都不许空着，ungrouped 也不许把词全收下")
    if len(groups) > max_families:
        errs.append(f"groups 有 {len(groups)} 组，最多 {max_families} 组")
    known = set(pool)
    seen: set[str] = set()
    claimed: set[str] = set()
    for i, g in enumerate(groups):
        tag = f"groups[{i}]"
        if not isinstance(g, dict):
            errs.append(f"{tag} 必须是对象")
            continue
        words = _word_list(g.get("words"))
        if words is None:
            errs.append(f'{tag}.words 必须是一个字符串，形如 "inspect, respect"，'
                        "不要把词写成对象的键")
            continue
        root = str(g.get("root", "")).lower()
        if not re.fullmatch(r"[a-z]{2,}", root):
            errs.append(f"{tag}.root 必须是2个以上小写英文字母")
        if not CJK.search(str(g.get("rootMeaning", ""))):
            errs.append(f"{tag}.rootMeaning 必须是汉字")
        for w in words:
            word = w.strip().lower()
            if word not in known:
                errs.append(f"{tag} 里的 {word} 不在用户词表里")
                continue
            seen.add(word)
            if word in claimed:
                errs.append(f"{word} 被分进了两个组")
            elif kind != "theme" and root and root not in word:
                errs.append(f"{tag} 里的 {word} 找不到词根 {root}")
            else:
                claimed.add(word)
    seen.update(w.strip().lower() for w in (_word_list(raw.get("ungrouped")) or []))
    if lost := [w for w in pool if w not in seen]:
        errs.append("这些词没交代清楚，要么分进某一组、要么写进 ungrouped：" + "、".join(lost[:8]))
    return errs


def _normalize_groups(raw: dict, pool: list[str], kind: str = "root") -> dict:
    """收下能用的组：结构坏掉的、人数不够的都丢掉，里面的词退回 ungrouped。"""
    groups: list[dict] = []
    covered: set[str] = set()
    for g in raw["groups"]:
        if not isinstance(g, dict):
            continue
        words = _word_list(g.get("words")) or []
        words = list(dict.fromkeys(w.strip().lower() for w in words))
        words = [w for w in words if w in set(pool) and w not in covered][:GROUP_MAX]
        if len(words) < GROUP_MIN:
            continue
        covered.update(words)
        groups.append({"root": str(g["root"]).strip().lower(),
                       "rootMeaning": str(g["rootMeaning"]).strip(),
                       "why": str(g.get("why", "")).strip(),
                       "kind": kind,
                       "words": words})
    return {"groups": groups, "ungrouped": [w for w in pool if w not in covered],
            "total": len(pool)}


class _BadGroups(llm.LlmError):
    """分组两轮都不合规。跟传输错误分开，好让调用方决定要不要退一步换个分法。"""


def _split(pool: list[str], system: str, max_families: int, kind: str,
           force: bool = False) -> tuple[list[dict], list[str]]:
    """一次分组调用，不合规就带着错误清单重试一次。返回 (分好的组, 剩下的词)。"""
    user = (f"下面是用户的词表，共 {len(pool)} 个词，请分成最多 {max_families} 组：\n"
            + "\n".join(pool))
    if force:
        user += ("\n\n这几个词找不到明显的共同点，但用户就是要一起记：请硬找一个能串起它们的场景"
                 "（同一个画面、同一件事、同一类感觉都行），把所有词都分进组里，ungrouped 留空。")
    problems: list[str] = []
    for temperature in (0.4, 0.1):
        raw = llm.complete_json(system, _user_with_errors(user, problems), temperature)
        if not isinstance(raw, dict):
            problems = ["返回值必须是一个 JSON 对象"]
            continue
        problems = _group_errors(raw, pool, max_families, kind, force)
        if not problems:
            done = _normalize_groups(raw, pool, kind)
            if done["groups"] or not force:
                return done["groups"], done["ungrouped"]
            problems = ["分出来的组都不合规，等于没分；请照上面的要求重分一次"]
    raise _BadGroups(f"模型两次都没分出合规的{'主题' if kind == 'theme' else '词根'}组："
                     + "；".join(problems[:6]))


# 把粘来的词表分组（只分组，不落库）
def group_words(text: str, max_families: int = 6) -> dict:
    """Split a pasted list into families: root groups first, then theme groups for the leftovers."""
    pool = parse_word_list(text)
    if not pool:
        raise llm.LlmError("没从输入里认出英文单词")
    if len(pool) == 1:
        # 只给了一个词根（或一个单词），没什么可分的，直接让生成阶段围着它写一族。
        return {"groups": [{"root": pool[0], "rootMeaning": "", "why": "", "kind": "root",
                            "words": []}], "ungrouped": [], "total": 1}
    try:
        groups, left = _split(pool, GROUP_SYSTEM, max_families, "root")
    except _BadGroups:
        groups, left = [], list(pool)   #按词根分不出来，整批交给主题分组再试一次
    room = max_families - len(groups)
    if room > 0 and len(left) >= GROUP_MIN:
        try:
            themes, rest = _split(left, THEME_GROUP_SYSTEM, room, "theme")
            groups += themes
            left = rest
        except _BadGroups:
            pass
    if not groups and len(left) >= GROUP_MIN:
        # 一组都没分出来时，模型多半是嫌这些词搭不上。用户既然写在一起就是想一起记，
        # 逼它硬找一个场景再试一次，实在找不出才回「凑不成一族」。
        try:
            groups, left = _split(left, THEME_GROUP_SYSTEM, max_families, "theme", force=True)
        except _BadGroups:
            pass
    return {"groups": groups, "ungrouped": left, "total": len(pool)}


def _user_with_errors(user: str, problems: list[str]) -> str:
    if not problems:
        return user
    return (user + "\n\n上一次输出有不合规的地方，请逐条修好，其他内容保持同等质量：\n"
            + "\n".join(f"- {p}" for p in problems[:12]))

# 手动输入词根
def store(fam: dict) -> Optional[int]:
    return repositories.add_family(fam, "agent")
