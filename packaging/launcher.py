"""双击就用的 exe 入口：静默起服务、开浏览器，退出走页面里的按钮。

跟 `python -m uvicorn app.main:app` 的差别有四处：打包后不能按字符串导入模块、不能开
reload、词库要先从包内复制到 exe 旁边，还有没有控制台窗口 —— 日志和端口都落到 data/ 里。
"""

from __future__ import annotations

import os
import shutil
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path


# 1、路径准备：非打包态（直接 python 跑这个文件调试）要把 backend 塞进 sys.path
FROZEN = getattr(sys, "frozen", False)
if not FROZEN:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

os.environ.setdefault("WORDMEMO_PORT", "8000")

from app import config  # noqa: E402  必须在定好端口之后再导入，config 读环境是导入时发生的
import uvicorn  # noqa: E402

PORT_FILE = "wordtree.port"      # 记当前实例占的端口，重复双击靠它认出"其实已经开着了"


# 2、首次运行把内置词库和配图复制到 exe 旁边的 data/
def materialize() -> None:
    """把打进包里的 starter 词库落到可写目录。已经存在就什么都不做，绝不覆盖用户进度。"""
    if not FROZEN:
        return
    starter = Path(sys._MEIPASS) / "starter"
    if not starter.is_dir() or config.DB_PATH.exists():
        return
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(starter / "wordmemo.db", config.DB_PATH)
    if (starter / "images").is_dir():
        shutil.copytree(starter / "images", config.IMAGES_DIR, dirs_exist_ok=True)


# 3、没有控制台窗口，输出得接到文件里才知道服务起没起来、报了什么
#    （冻结态下 sys.stdout 是个吞字的 NullWriter，不是 None，所以按打包与否判断）
def attach_log() -> None:
    if not FROZEN:
        return
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    stream = open(config.DATA_DIR / "wordtree.log", "w", encoding="utf-8", buffering=1)
    sys.stdout = sys.stderr = stream


# 4、已有实例还活着就复用它的地址
def alive_url() -> str:
    """端口文件里的服务能答 /api/health 才算活着；答不上就当作上次被杀了，重新起一个。"""
    path = config.DATA_DIR / PORT_FILE
    if not path.is_file():
        return ""
    try:
        port = int(path.read_text().strip())
        with urllib.request.urlopen(f"http://{config.HOST}:{port}/api/health", timeout=0.5) as r:
            return f"http://{config.HOST}:{port}/" if r.status == 200 else ""
    except Exception:
        return ""


# 5、挑一个没人占的端口
def free_port(preferred: int) -> int:
    """从首选端口往后试 20 个，返回第一个能 bind 上的。全占满就直接退出，别悄悄挑到别处在用的端口。"""
    for port in range(preferred, preferred + 20):
        with socket.socket() as probe:
            try:
                probe.bind((config.HOST, port))
            except OSError:
                continue
            return port
    raise SystemExit(f"{preferred} 起的 20 个端口都被占了，先关掉另一个 WordTree")


# 6、等服务真的开始监听了再开浏览器，不然第一跳是拒绝连接
def open_later(url: str, server: "uvicorn.Server") -> None:
    while not server.started:
        if server.should_exit:
            return
        time.sleep(0.1)
    webbrowser.open(url)


def main() -> None:
    materialize()
    if url := alive_url():          # 已经开着了：这只是一种"再开一个标签页"
        webbrowser.open(url)
        return

    attach_log()
    port = free_port(int(os.environ["WORDMEMO_PORT"]))
    url = f"http://{config.HOST}:{port}/"

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    (config.DATA_DIR / PORT_FILE).write_text(str(port))

    from app.main import app  # noqa: E402  放这里：导入即建库、挂静态，得等路径都定了

    server = uvicorn.Server(uvicorn.Config(app, host=config.HOST, port=port, log_level="info"))
    threading.Thread(target=open_later, args=(url, server), daemon=True).start()

    print(f"单词记忆Web应用  {url}")
    print(f"数据目录  {config.DATA_DIR}")
    print("退出：页面右下角「退出程序」，或在任务管理器结束 WordTree.exe。")
    try:
        server.run()
    finally:
        (config.DATA_DIR / PORT_FILE).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
