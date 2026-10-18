#!/bin/bash
set -e
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
for candidate in "$HOME"/.local/node-*/bin; do
  if [ -d "$candidate" ]; then export PATH="$candidate:$PATH"; fi
done
if [ ! -x ".venv/bin/python" ]; then
  if command -v uv >/dev/null 2>&1; then uv venv --python 3.11 .venv
  elif command -v python3 >/dev/null 2>&1; then python3 -m venv .venv
  else echo "首次安装需要 Python 3.11 或更新版，请安装后再次打开。"; read -r; exit 1; fi
fi
if [ ! -f ".venv/toolbox-ready" ]; then
  REQS=requirements.txt
  if command -v ffmpeg >/dev/null 2>&1; then REQS=requirements-core.txt; fi
  if command -v uv >/dev/null 2>&1; then uv pip install --python .venv/bin/python -r "$REQS"
  else .venv/bin/python -m pip install -r "$REQS"; fi
  touch .venv/toolbox-ready
fi
if command -v npm >/dev/null 2>&1; then
  if [ ! -d video/node_modules ]; then npm ci --prefix video --no-audit --no-fund; fi
  if [ ! -f video/.browser-ready ]; then
    (cd video && npx playwright install chromium)
    touch video/.browser-ready
  fi
else
  echo "视频功能需要 Node.js。图文工具仍可打开；安装 Node.js 后再次启动可启用视频。"
fi
exec .venv/bin/python start.py
