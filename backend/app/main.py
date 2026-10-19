"""FastAPI entry point: CORS, static assets, routers, boot-time schema + seed."""
from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import config, db, seed
from .routers import families, generation, settings, study


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    seed.seed_if_empty()
    yield


app = FastAPI(title="WordMemo API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(families.router)
app.include_router(study.router)
app.include_router(generation.router)
app.include_router(settings.router)

if config.ASSETS_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=config.ASSETS_DIR), name="assets")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "db": str(config.DB_PATH), "llm": config.llm_ready(),
            "model": config.DEEPSEEK_MODEL, "imageProvider": config.IMAGE_PROVIDER}


def main() -> None:
    uvicorn.run("app.main:app", host=config.HOST, port=config.PORT, reload=True)


# 装在最后："/" 会吃掉后面注册的路由。构建过前端时，一个进程就能同时给 API 和页面。
if config.DIST_DIR.is_dir():
    app.mount("/", StaticFiles(directory=config.DIST_DIR, html=True), name="spa")


if __name__ == "__main__":
    main()
