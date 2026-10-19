"""Route layer: ask the agent layer for a new family, polled by job id."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException

from .. import config, repositories, schemas
from ..agents import family_agent, llm

router = APIRouter(prefix="/api/generate", tags=["generation"])


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


@router.post("")
def start(body: schemas.GenerateRequest, background: BackgroundTasks) -> dict:
    if not config.llm_ready():
        raise HTTPException(503, "后端没有配置 DEEPSEEK_API_KEY，生成词族不可用")
    job_id = uuid.uuid4().hex[:12]
    repositories.create_job(job_id, body.keyword)
    background.add_task(run_job, job_id, body.keyword, body.words)
    return {"jobId": job_id, "status": "pending", "keyword": body.keyword}


@router.get("/{job_id}")
def status(job_id: str) -> dict:
    job = repositories.get_job(job_id)
    if not job:
        raise HTTPException(404, "没有这个生成任务")
    return {"jobId": job["id"], "status": job["status"], "keyword": job["keyword"],
            "familyId": job["family_id"], "error": job["error"]}
