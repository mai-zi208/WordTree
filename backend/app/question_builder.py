"""学习/测验侧的“出题引擎”：把词库里静态单词行渲染成前端的5种题型
study.py(路由) → pool_words/due_words(选词) → build_queue(选题型) → build_item(造题) → 前端
"""
from __future__ import annotations

import random
from typing import Any, Optional

from . import repositories, scheduling

TAGS = {   #题型
    "gloss": "看词猜义",
    "meme": "看梗反推词",
    "cloze": "例句填空",
    "order": "词块成句",
    "picture": "看图解词",
}


def shuffle(items: list) -> list:
    return random.sample(items, len(items))


def kinds_for(word: dict) -> list[str]:
    kinds = ["gloss", "meme", "cloze", "order"]
    if word.get("img"):
        kinds.append("picture")
    return kinds

# 选项只取同族词
def _word_options(word: dict, siblings: list[dict]) -> tuple[list[str], list[str]]:
    """干扰项取同族词。返回 (选项, 与选项下标对齐的中文释义)。"""
    picks = shuffle([w for w in siblings if w["word"] != word["word"]])[:3] + [word]
    return [w["word"] for w in picks], [w["gloss"] for w in picks]

# 给正确答案
def _gloss_options(word: dict, siblings: list[dict]) -> tuple[list[str], list[str]]:
    """考释义时选项反过来：中文当选项，英文原词当答案页的注解。"""
    picks = shuffle([w for w in siblings if w["word"] != word["word"]])[:3] + [word]
    return [w["gloss"] for w in picks], [w["word"] for w in picks]


def _sentence_zh(word: dict) -> Optional[str]:
    """例句恰好就是内容句时，把它的中文翻译带上，答题后一起显示。"""
    if word["content_type"] == "sentence" and word["content_en"] == word["example"]:
        return word["content_zh"]
    return None


def _hint(kind: str, word: dict) -> str:
    if kind == "gloss":
        return word["meme"]
    if kind == "picture":
        return f"{word['img_zh']}　→　{word['word']} {word['gloss']}"
    return f"{word['example']}　（{word['gloss']}）"


def as_url(rel: Optional[str]) -> Optional[str]:
    return "/" + rel.lstrip("/") if rel else None


def build_item(kind: str, word: dict, family: dict) -> Optional[dict]:
    siblings = family["words"]
    item: dict[str, Any] = {
        "kind": kind,
        "word": word["word"],
        "familyId": family["id"],
        "stem": {"tag": TAGS[kind]},
    }
    if kind == "gloss":
        item["stem"]["word"] = word["word"]
        item["options"], item["optionNotes"] = _gloss_options(word, siblings)
        item["answer"] = word["gloss"]
    elif kind == "meme":
        item["stem"]["text"] = word["meme"]
        item["options"], item["optionNotes"] = _word_options(word, siblings)
        item["answer"] = word["word"]
    elif kind == "picture":
        item["stem"]["img"] = as_url(word["img"])
        item["stem"]["imgAlt"] = word["img_zh"]
        item["options"], item["optionNotes"] = _word_options(word, siblings)
        item["answer"] = word["word"]
    elif kind == "cloze":
        item["stem"]["text"] = word["example"].replace(word["blank"], "______")
        item["stem"]["note"] = "句中这个词已变形，按词义选原形"
        item["options"], item["optionNotes"] = _word_options(word, siblings)
        item["answer"] = word["word"]
    elif kind == "order":
        item["stem"]["note"] = "按顺序点下面的词块，拼出这句英文"
        tokens = word["example"].split(" ")
        chips = shuffle(list(range(len(tokens))))
        if [tokens[i] for i in chips] == tokens and len(tokens) > 1:
            chips = chips[::-1]
        item["tokens"] = tokens
        item["chips"] = [tokens[i] for i in chips]
        item["answer"] = word["example"]
    else:
        return None
    item["hint"] = _hint(kind, word)
    if zh := _sentence_zh(word):
        item["zh"] = zh
    return item

# 只管拿到词后造题
def build_queue(words: list[dict], per_word: int) -> list[dict]:
    fams = {f["id"]: f for f in repositories.list_families()}
    items: list[dict] = []
    for word in words:
        kinds = shuffle(kinds_for(word))   #随机选题型
        count = max(1, min(per_word, len(kinds)))
        if count > 1 and "meme" not in kinds[:count]:
            kinds[count - 1] = "meme"   #至少有一道meme题
        for kind in kinds[:count]:
            item = build_item(kind, word, fams[word["family_id"]])
            if item:
                items.append(item)
    return shuffle(items)

# 从reviews表筛词
def pool_words(family: dict, pool: str) -> list[dict]:
    reviews = repositories.reviews()
    today = scheduling.today()

    def rated(w):
        return reviews.get(w["word"])

    if pool == "fresh":
        words = [w for w in family["words"] if w["word"] not in reviews]
    elif pool == "due":
        words = [w for w in family["words"]
                 if (r := rated(w)) and r["next_date"] and r["next_date"] <= today]
    elif pool == "weak":
        words = [w for w in family["words"]
                 if (r := rated(w)) and (r["stage"] <= 2 or r["wrong"] > 0)]
    else:
        words = list(family["words"])
    return words or list(family["words"])

# 单独服务复习模式
def due_words() -> list[dict]:
    today = scheduling.today()
    reviews = repositories.reviews()
    return [w for w in repositories.all_words()
            if (r := reviews.get(w["word"])) and r["next_date"] and r["next_date"] <= today]
