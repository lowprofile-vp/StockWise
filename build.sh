#!/usr/bin/env bash
# Render build. Works from the repository root or from backend/.
set -euo pipefail

if [ -f backend/requirements.txt ]; then
  ROOT="$PWD"
elif [ -f requirements.txt ] && [ -d ../frontend ]; then
  ROOT="$(cd .. && pwd)"
else
  echo "Run build.sh from the StockWise repository." >&2
  exit 1
fi

cd "$ROOT"
pip install -r backend/requirements.txt

if ! command -v npm >/dev/null 2>&1; then
  NODE_VERSION="$(python -c "import json,urllib.request; rels=json.load(urllib.request.urlopen('https://nodejs.org/dist/index.json')); print(next(r['version'] for r in rels if r['version'].startswith('v22.')))")"
  curl -fsSL "https://nodejs.org/dist/${NODE_VERSION}/node-${NODE_VERSION}-linux-x64.tar.gz" -o /tmp/node.tar.gz
  tar -xzf /tmp/node.tar.gz -C /tmp
  export PATH="/tmp/node-${NODE_VERSION}-linux-x64/bin:${PATH}"
fi

npm --prefix frontend ci
npm --prefix frontend run build
