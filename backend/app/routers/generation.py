"""路由层：生成词族"""
from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException

from .. import config, repositories, schemas
from ..agents import family_agent

router = APIRouter(prefix="/api/generate", tags=["generation"])


def _need_llm() -> None:
    if not config.llm_ready():
        raise HTTPException(503, "还没配置模型密钥，先在首页右上角的设置里填上")


def _new_job(kind: str, label: str, total: int = 0) -> str:
    job_id = uuid.uuid4().hex[:12]
    repositories.create_job(job_id, label, kind, total)
    return job_id

# 分组
def run_group_job(job_id: str, text: str, max_families: int) -> None:
    repositories.running_job(job_id)
    try:
        repositories.succeed_job(job_id, None, family_agent.group_words(text, max_families))
    except Exception as exc:
        repositories.fail_job(job_id, str(exc))

# 批量生成到暂存区
def run_batch_job(job_id: str, groups: list[dict]) -> None:
    """Generate the chosen groups one by one into the job row.

    这一步不碰词库：内容先躺在 result_json 里给用户预览，用户点「加入便签墙」才由 save 落库。
    一族失败不影响其他族。
    """
    repositories.running_job(job_id)
    known = {w["word"] for w in repositories.all_words()}
    staged: set[str] = set()   #同一次批量里已经生成好的词，别让两族撞同一个新词
    results: list[dict] = []
    for index, group in enumerate(groups):
        wanted = [str(w).lower() for w in group.get("words") or []]
        fresh = [w for w in wanted if w not in known]
        entry: dict = {"root": group["root"].lower(), "kind": group.get("kind", "root"),
                       "rootMeaning": group.get("rootMeaning", ""), "words": wanted, "ok": False}
        if wanted and len(fresh) < 2:
            entry["dupes"] = [w for w in wanted if w in known]
            entry["error"] = "这些词已经在词库里了，凑不出新的一组"
        else:
            try:
                fam = family_agent.generate_group({**group, "words": fresh}, extra_known=staged)
                staged.update(w["word"] for w in fam["words"])
                entry.update(ok=True, root=fam["root"], rootMeaning=fam["rootMeaning"],
                             family=fam)
                if wanted:
                    entry["dupes"] = [w for w in wanted if w in known]
            except Exception as exc:
                entry["error"] = str(exc)
        results.append(entry)
        repositories.job_progress(job_id, index + 1, {"results": results})
    if any(r["ok"] for r in results):
        repositories.succeed_job(job_id, None, {"results": results})
    else:
        repositories.fail_job(job_id, f"{len(results)} 个词族都没生成成功", {"results": results})

# 粘一批词或给一个词根，先分组（不落库）
@router.post("/group")
def start_group(body: schemas.GroupRequest, background: BackgroundTasks) -> dict:
    _need_llm()
    label = " ".join(body.text.split())[:40]
    job_id = _new_job("group", label)
    background.add_task(run_group_job, job_id, body.text, body.max_families)
    return {"jobId": job_id, "status": "pending", "kind": "group", "keyword": label}

# 把选中的组逐条生成到暂存区
@router.post("/batch")
def start_batch(body: schemas.BatchRequest, background: BackgroundTasks) -> dict:
    _need_llm()
    label = "、".join(g.root for g in body.groups)[:40]
    job_id = _new_job("batch", label, total=len(body.groups))
    background.add_task(run_batch_job, job_id, [g.model_dump() for g in body.groups])
    return {"jobId": job_id, "status": "pending", "kind": "batch",
            "keyword": label, "total": len(body.groups)}

# 用户在预览里挑中的族，这一步才真正进词库
@router.post("/{job_id}/save")
def save(job_id: str, body: schemas.SaveRequest) -> dict:
    job = repositories.get_job(job_id)
    if not job or not job["result_json"]:
        raise HTTPException(404, "这份预览已经过期，重新生成一次")
    try:
        results = (json.loads(job["result_json"]) or {}).get("results") or []
    except json.JSONDecodeError:
        results = []
    saved, skipped = [], []
    for pick in body.picks:
        if not 0 <= pick < len(results):
            continue
        entry = results[pick]
        if not entry.get("ok") or not entry.get("family"):
            continue
        family_id = family_agent.store(entry["family"])
        if family_id is None:
            skipped.append({"root": entry["root"], "error": f"词根 {entry['root']} 已经在词库里"})
        else:
            saved.append({"root": entry["root"], "familyId": family_id,
                          "words": len(entry["family"]["words"])})
    repositories.delete_job(job_id)   #存完就把暂存清掉，库里不留副本
    return {"saved": saved, "skipped": skipped}

# 用户不要了：连暂存内容一起丢掉
@router.delete("/{job_id}")
def discard(job_id: str) -> dict:
    repositories.delete_job(job_id)
    return {"discarded": True}

# 轮询端点
@router.get("/{job_id}")
def status(job_id: str) -> dict:
    job = repositories.get_job(job_id)
    if not job:
        raise HTTPException(404, "没有这个生成任务")
    try:
        result = json.loads(job["result_json"]) if job["result_json"] else None
    except json.JSONDecodeError:
        result = None
    return {"jobId": job["id"], "status": job["status"], "kind": job["kind"],
            "keyword": job["keyword"], "familyId": job["family_id"], "error": job["error"],
            "total": job["total"], "done": job["done"], "result": result}
