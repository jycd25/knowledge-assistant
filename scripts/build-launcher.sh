#!/usr/bin/env bash
# Build the web UI into the Python package, build the wheel, and stage it in the npm launcher.
set -euo pipefail
cd "$(dirname "$0")/.."
(cd web && npm run build)
rm -rf launcher/python dist && mkdir -p launcher/python
.venv/bin/pip wheel . --no-deps -w launcher/python -q
cp README.md launcher/README.md
echo "launcher ready:"; ls -la launcher/python
echo "run locally with: node launcher/bin/ka.js  (package is marked private; not published)"
