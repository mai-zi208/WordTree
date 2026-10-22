"""路由层：给词配图。单张同步出，整族走后台任务，进度跟生成词族共用一套轮询。"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException

from .. import config, repositories, serializer
from ..agents import image_agent

router = APIRouter(prefix="/api/images", tags=["images"])


def _need_image() -> None:
    if not config.image_ready():
        raise HTTPException(503, "还没开生图：去设置里把出图服务打成 dashscope，密钥跟聊天共用一把")


def _draw(row: dict) -> dict:
    """出一张图、写回库、返回前端要的形状。"""
    img, caption = image_agent.generate(row)
    if not repositories.set_word_image(row["word"], img, caption):
        raise image_agent.ImageError(f"词库里没有 {row['word']}，图画好了也没处挂")
    return {"word": row["word"], "img": serializer.as_url(img), "imgZh": caption}


# 单个词配图：一张图几秒钟，同步等着就行，不用建任务
@router.post("/word/{word}")
def draw_word(word: str) -> dict:
    _need_image()
    row = repositories.get_word(word)
    if not row:
        raise HTTPException(404, f"词库里没有 {word}")
    try:
        return _draw(row)
    except image_agent.ImageError as exc:
        raise HTTPException(502, str(exc)) from exc


def run_family_job(job_id: str, family_id: int, todo: list[str]) -> None:
    """逐词补图。一张失败不影响其他张，失败的词记在结果里给用户看。"""
    repositories.running_job(job_id)
    images: list[dict] = []
    for index, word in enumerate(todo):
        row = repositories.get_word(word)
        if not row:
            continue
        try:
            images.append(_draw(row) | {"ok": True})
        except Exception as exc:
            images.append({"word": word, "ok": False, "error": str(exc)})
        repositories.job_progress(job_id, index + 1, {"images": images})
    failed = [i for i in images if not i["ok"]]
    if failed:
        repositories.fail_job(job_id, f"{len(failed)} 张图没出来：{failed[0]['error']}",
                              {"images": images})
    else:
        repositories.succeed_job(job_id, family_id, {"images": images})


# 整族补图：一族最多十几张，走后台任务，前端轮询进度
@router.post("/family/{family_id}")
def start_family(family_id: int, background: BackgroundTasks) -> dict:
    _need_image()
    fam = repositories.get_family(family_id)
    if not fam:
        raise HTTPException(404, "找不到这个词族")
    todo = [w["word"] for w in fam["words"] if not w["img"]]
    if not todo:
        raise HTTPException(400, "这一族的图都齐了，想换一张就点开大图重画")
    job_id = uuid.uuid4().hex[:12]
    repositories.create_job(job_id, fam["root"], "image", len(todo))
    background.add_task(run_family_job, job_id, family_id, todo)
    return {"jobId": job_id, "status": "pending", "kind": "image",
            "keyword": fam["root"], "total": len(todo)}
