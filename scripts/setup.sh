#!/usr/bin/env bash
# One-shot local setup for MCP-GuardID backend.
#
# WHY THIS SCRIPT EXISTS: on machines with multiple Python installs (conda +
# system + python.org framework builds, common on macOS), `pip install ...`
# and a later bare `python ...` can silently resolve to TWO DIFFERENT
# interpreters, so packages you just installed appear "missing", or a
# polluted global site-packages (old pandas/pyarrow built against numpy 1.x)
# crashes on import once numpy 2.x is pulled in. An isolated virtualenv
# sidesteps both problems: `python` and `pip` inside it are guaranteed to be
# the same interpreter, and it starts with nothing else installed.
#
# Usage:
#   bash scripts/setup.sh
#   source .venv/bin/activate        # then, in every NEW terminal you open
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "==> Using base interpreter: $(command -v "$PYTHON_BIN")"
"$PYTHON_BIN" --version

echo "==> Creating isolated virtual environment at .venv"
"$PYTHON_BIN" -m venv .venv

# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Confirming python/pip resolve inside .venv:"
which python
which pip

echo "==> Installing dependencies"
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Generating synthetic datasets"
python -m scripts.generate_dataset

echo "==> Seeding the database"
python -m scripts.seed_database

cat <<'EOF'

==> Setup complete.

IMPORTANT: every time you open a NEW terminal to work on this project, run:
    source .venv/bin/activate
first, so `python`/`pip`/`uvicorn` all resolve inside this same environment.

Next steps:
  cd backend && PYTHONPATH=".:.." uvicorn main:app --reload
  (in another terminal) cd frontend && npm install && npm run dev
EOF
