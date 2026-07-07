#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "== Phase A: Python syntax checks =="
python -m py_compile \
  backend/app/worker.py \
  backend/app/extraction/*.py \
  backend/app/documents/storage.py \
  backend/app/documents/service.py \
  backend/app/documents/router.py \
  backend/app/config/settings.py

if python -c "import sqlalchemy, celery, fastapi" >/dev/null 2>&1; then
  echo "== Phase A: backend targeted pytest =="
  PYTHONPATH=backend python -m pytest -q \
    backend/tests/test_extraction_static.py \
    backend/tests/test_extraction_enqueue.py \
    backend/tests/test_document_versions_static.py \
    backend/tests/test_document_acl_static.py
else
  echo "WARN: Python backend dependencies are not installed; skipping local pytest." >&2
  echo "      Run: python -m pip install -r backend/requirements.txt" >&2
fi

if command -v npm >/dev/null 2>&1; then
  echo "== Phase A: frontend checks =="
  (cd frontend && npm ci && npm run test:auth && npm run test:documents && npm run type-check && npm run lint && npm run build)
else
  echo "WARN: npm is not installed; skipping frontend checks." >&2
fi

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  echo "== Phase A: Docker Compose config/build/import/migration checks =="
  docker compose --profile test --profile worker config >/dev/null
  docker compose --profile test build backend-test
  docker compose --profile worker build worker
  docker compose run --rm --no-deps backend python -c "from app.main import app; print('backend-import-ok')"
  docker compose --profile worker run --rm --no-deps worker python -c "from app.worker import celery_app; print('worker-import-ok', celery_app.main)"
  docker compose run --rm backend alembic heads
  docker compose run --rm backend alembic current || true
  echo "Run 'docker compose run --rm backend alembic upgrade head' when dependencies are healthy and DB is reachable."
else
  echo "WARN: Docker CLI/Compose plugin unavailable; skipping Docker checks." >&2
fi

echo "Phase A verification script completed. Review WARN lines before Phase B."
