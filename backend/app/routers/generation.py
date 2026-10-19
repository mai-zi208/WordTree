"""Route layer: ask the agent layer for new families, polled by job id."""
from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException

from .. import config, repositories, schemas
from ..agents import family_agent, llm

router = APIRouter(prefix="/api/generate", tags=["generation"])


def _need_llm() -> None:
    if not config.llm_ready():
        raise HTTPException(503, "还没配置模型密钥，先在首页右上角的设置里填上")


def _new_job(kind: str, label: str, total: int = 0) -> str:
    job_id = uuid.uuid4().hex[:12]
    repositories.create_job(job_id, label, kind, total)
    return job_id


def run_job(job_id: str, keyword: str, words: int) -> None:
    repositories.running_job(job_id)
    try:
        fam = family_agent.generate_family(keyword, words)
        family_id = family_agent.store(fam)
        if family_id is None:
            raise llm.LlmError(f"词根 {fam['root']} 已经在词库里")
        repositories.succeed_job(job_id, family_id)
    except Exception as exc:
        repositories.fail_job(job_id, str(exc))


def run_group_job(job_id: str, text: str, max_families: int) -> None:
    repositories.running_job(job_id)
    try:
        repositories.succeed_job(job_id, None, family_agent.group_words(text, max_families))
    except Exception as exc:
        repositories.fail_job(job_id, str(exc))


def run_batch_job(job_id: str, groups: list[dict]) -> None:
    """Generate the chosen groups one by one; one bad group doesn't kill the rest."""
    repositories.running_job(job_id)
    known = {w["word"] for w in repositories.all_words()}
    results: list[dict] = []
    for index, group in enumerate(groups):
        root = group["root"].lower()
        fresh = [w for w in group["words"] if w not in known]
        entry: dict = {"root": root, "words": group["words"], "ok": False}
        if len(fresh) < 2:
            entry["error"] = "这些词已经在词库里了"
        else:
            try:
                fam = family_agent.generate_family(root, allowed=fresh)
                family_id = family_agent.store(fam)
                if family_id is None:
                    entry["error"] = f"词根 {fam['root']} 已经在词库里"
                else:
                    known.update(fresh)
                    entry.update(ok=True, familyId=family_id, root=fam["root"])
            except Exception as exc:
                entry["error"] = str(exc)
        results.append(entry)
        repositories.job_progress(job_id, index + 1, {"results": results})
    if any(r["ok"] for r in results):
        repositories.succeed_job(job_id, None, {"results": results})
    else:
        repositories.fail_job(job_id, f"{len(results)} 个词族都没生成成功", {"results": results})


@router.post("")
def start(body: schemas.GenerateRequest, background: BackgroundTasks) -> dict:
    _need_llm()
    job_id = _new_job("family", body.keyword)
    background.add_task(run_job, job_id, body.keyword, body.words)
    return {"jobId": job_id, "status": "pending", "kind": "family", "keyword": body.keyword}


@router.post("/group")
def start_group(body: schemas.GroupRequest, background: BackgroundTasks) -> dict:
    _need_llm()
    label = " ".join(body.text.split())[:40]
    job_id = _new_job("group", label)
    background.add_task(run_group_job, job_id, body.text, body.max_families)
    return {"jobId": job_id, "status": "pending", "kind": "group", "keyword": label}


@router.post("/batch")
def start_batch(body: schemas.BatchRequest, background: BackgroundTasks) -> dict:
    _need_llm()
    label = "、".join(g.root for g in body.groups)[:40]
    job_id = _new_job("batch", label, total=len(body.groups))
    background.add_task(run_batch_job, job_id, [g.model_dump() for g in body.groups])
    return {"jobId": job_id, "status": "pending", "kind": "batch",
            "keyword": label, "total": len(body.groups)}


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
