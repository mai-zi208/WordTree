"""Turn stored word rows into fully materialized quiz items (5 question types)."""
from __future__ import annotations

import random
from typing import Any, Optional

from . import repositories, scheduling

TAGS = {
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


def _word_options(word: dict, siblings: list[dict]) -> list[str]:
    distractors = [w["word"] for w in siblings if w["word"] != word["word"]]
    return shuffle(distractors)[:3] + [word["word"]]


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
        item["options"] = shuffle(
            [w["gloss"] for w in siblings if w["word"] != word["word"]])[:3] + [word["gloss"]]
        item["answer"] = word["gloss"]
    elif kind == "meme":
        item["stem"]["text"] = word["meme"]
        item["options"] = _word_options(word, siblings)
        item["answer"] = word["word"]
    elif kind == "picture":
        item["stem"]["img"] = as_url(word["img"])
        item["stem"]["imgAlt"] = word["img_zh"]
        item["options"] = _word_options(word, siblings)
        item["answer"] = word["word"]
    elif kind == "cloze":
        item["stem"]["text"] = word["example"].replace(word["blank"], "______")
        item["stem"]["note"] = "句中这个词已变形，按词义选原形"
        item["options"] = _word_options(word, siblings)
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
    return item


def build_queue(words: list[dict], per_word: int) -> list[dict]:
    fams = {f["id"]: f for f in repositories.list_families()}
    items: list[dict] = []
    for word in words:
        kinds = shuffle(kinds_for(word))
        count = max(1, min(per_word, len(kinds)))
        if count > 1 and "meme" not in kinds[:count]:
            kinds[count - 1] = "meme"
        for kind in kinds[:count]:
            item = build_item(kind, word, fams[word["family_id"]])
            if item:
                items.append(item)
    return shuffle(items)


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


def due_words() -> list[dict]:
    today = scheduling.today()
    reviews = repositories.reviews()
    return [w for w in repositories.all_words()
            if (r := reviews.get(w["word"])) and r["next_date"] and r["next_date"] <= today]
