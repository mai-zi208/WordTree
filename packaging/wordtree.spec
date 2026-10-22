# -*- coding: utf-8 -*-
"""单文件 WordTree.exe：前端产物和插图打进只读区，词库以 starter 形式随包发布。

构建：packaging/build.sh（会先建 .venv-pack 再装 pyinstaller）。
数据不落包里 —— exe 旁边的 data/ 和 .env 才是运行时真正读写的地方。
"""

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).resolve().parent
BACKEND = ROOT / "backend"
DIST = ROOT / "web" / "dist"
ASSETS = ROOT / "assets"
SEED_DB = Path(SPECPATH) / "starter" / "wordmemo.db"   # make_starter.py 生成的脱敏副本
SEED_IMAGES = BACKEND / "data" / "images"

if not DIST.is_dir():
    raise SystemExit("web/dist 不存在，先在 web/ 下 npm run build")
if not SEED_DB.is_file():
    raise SystemExit("packaging/starter/wordmemo.db 不存在，请走 packaging/build.sh（它会先生成脱敏副本）")

datas = [
    (str(DIST), "web/dist"),                    # main.py 挂 / 用的是 config.RESOURCE_DIR/web/dist
    (str(ASSETS), "assets"),                    # 手绘种子插画
    (str(BACKEND / "app" / "seed_data.json"), "app"),   # config.SEED_FILE 指着的位置
]
if SEED_DB.is_file():
    datas.append((str(SEED_DB), "starter"))     # 脱敏起始库，首次运行由 launcher 复制到 exe 旁边
if SEED_IMAGES.is_dir():
    datas.append((str(SEED_IMAGES), "starter/images"))

a = Analysis(
    [str(Path(SPECPATH) / "launcher.py")],
    pathex=[str(BACKEND)],
    datas=datas,
    hiddenimports=collect_submodules("uvicorn"),
    excludes=["tkinter", "pytest"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="WordTree",
    debug=False,
    strip=False,
    upx=False,
    console=False,       # 不弹黑窗口：日志落 data/wordtree.log，退出走页面里的按钮
    icon=None,
)
