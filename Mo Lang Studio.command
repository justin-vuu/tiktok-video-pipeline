#!/bin/zsh
cd "$(dirname "$0")"
if [ ! -x ".venv-web/bin/python" ]; then
  python3 -m venv .venv-web || exit 1
  .venv-web/bin/python -m pip install -r requirements-web.txt || exit 1
fi
if curl --silent --fail http://127.0.0.1:7860/api/health >/dev/null; then
  open http://127.0.0.1:7860
  exit 0
fi
(.venv-web/bin/python -c 'import time, webbrowser; time.sleep(2); webbrowser.open("http://127.0.0.1:7860")') &
.venv-web/bin/python -m studio.server
