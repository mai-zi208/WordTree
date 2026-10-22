#!/usr/bin/env bash
# 重打单文件 exe：产出 packaging/dist/WordTree.exe。
# 打包用独立 venv（.venv-pack），不碰开发用的 .venv，也不往系统 Python 里装东西。
set -euo pipefail
cd "$(dirname "$0")/.."

PY=3.11                      # pyinstaller 对 3.14 的支持还没跟上，钉死一个能用的
[ -d .venv-pack ] || uv venv --python "$PY" .venv-pack
uv pip install --python .venv-pack -r backend/requirements.txt pyinstaller
.venv-pack/Scripts/pyinstaller.exe --noconfirm \
  --distpath packaging/dist --workpath packaging/build packaging/wordtree.spec

ls -lh packaging/dist/WordTree.exe
