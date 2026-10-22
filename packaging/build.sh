#!/usr/bin/env bash
# 重打单文件 exe：产出 packaging/dist/WordTree.exe。
# 打包用独立 venv（.venv-pack），不碰开发用的 .venv，也不往系统 Python 里装东西。
set -euo pipefail
cd "$(dirname "$0")/.."

PY=3.11                      # pyinstaller 对 3.14 的支持还没跟上，钉死一个能用的

# 前端产物比源码旧就别往下打：打进包里的永远是 dist 那一坨，
# 改了 .vue 没重新 build，出去的就是"点了没反应"的 exe，比构建失败难查十倍。
[ -f web/dist/index.html ] || { echo "web/dist 不存在，先 cd web && npm run build"; exit 1; }
if [ -n "$(find web/src web/index.html web/vite.config.js -newer web/dist/index.html -print -quit 2>/dev/null)" ]; then
  echo "web/dist 比源码旧（有 .vue/.js 改过没重新构建），先 cd web && npm run build"
  exit 1
fi

[ -d .venv-pack ] || uv venv --python "$PY" .venv-pack
uv pip install --python .venv-pack -r backend/requirements.txt pyinstaller

# 打进包里的词库是脱敏副本，不带你的复习记录
.venv-pack/Scripts/python.exe packaging/make_starter.py

.venv-pack/Scripts/pyinstaller.exe --noconfirm \
  --distpath packaging/dist --workpath packaging/build packaging/wordtree.spec

ls -lh packaging/dist/WordTree.exe
