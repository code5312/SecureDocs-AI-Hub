#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TARGETED_TESTS=(
  tests/test_extraction_static.py
  tests/test_extraction_enqueue.py
  tests/test_document_versions_static.py
  tests/test_document_acl_static.py
)

run_python_syntax() {
  echo "== Phase A: Python syntax checks =="
  python -m py_compile \
    backend/app/worker.py \
    backend/app/extraction/*.py \
    backend/app/documents/storage.py \
    backend/app/documents/service.py \
    backend/app/documents/router.py \
    backend/app/config/settings.py \
    scripts/extraction_smoke_test.py
}

run_frontend_checks() {
  if command -v npm >/dev/null 2>&1; then
    echo "== Phase A: frontend checks =="
    (cd frontend && npm ci && npm run test:auth && npm run test:documents && npm run type-check && npm run lint && npm run build)
  else
    echo "WARN: npm is not installed; skipping frontend checks." >&2
  fi
}

run_host_backend_tests() {
  if python -c "import sqlalchemy, celery, fastapi" >/dev/null 2>&1; then
    echo "== Phase A: host backend targeted pytest =="
    (cd backend && python -m pytest -q "${TARGETED_TESTS[@]}")
  else
    echo "ERROR: Docker is unavailable and Python backend dependencies are not installed." >&2
    echo "Install dependencies with Python 3.12 or use Docker: python -m pip install -r backend/requirements.txt" >&2
    return 1
  fi
}

wait_for_healthy() {
  local service="$1"
  local lines="${2:-200}"
  echo "Waiting for $service to become healthy..."
  for _ in {1..60}; do
    local container_id
    container_id="$(docker compose ps -q "$service")"
    if [[ -n "$container_id" ]]; then
      local status
      status="$(docker inspect "$container_id" --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}')"
      if [[ "$status" == "healthy" || "$status" == "running" ]]; then
        echo "$service status: $status"
        return 0
      fi
    fi
    sleep 2
  done
  echo "ERROR: $service did not become healthy." >&2
  docker compose ps -a >&2 || true
  docker compose logs --tail="$lines" "$service" >&2 || true
  exit 1
}

run_docker_phase_a() {
  echo "== Phase A: Docker Compose checks =="
  docker compose --profile test --profile worker config >/dev/null
  docker compose --profile test --profile worker config --format json | python -c '
import json, sys
services = json.load(sys.stdin)["services"]
for name in ("backend", "backend-test", "worker"):
    env = services[name].get("environment", {})
    assert env.get("POSTGRES_HOST") == "postgres"
    assert env.get("REDIS_URL") == "redis://redis:6379/0"
    assert env.get("CELERY_BROKER_URL") == "redis://redis:6379/1"
    assert env.get("MINIO_ENDPOINT") == "minio:9000"
assert "worker" in services["worker"].get("profiles", [])
assert "test" in services["backend-test"].get("profiles", [])
'
  docker compose --profile test --profile worker down --remove-orphans
  docker compose build backend
  docker compose --profile test build backend-test
  docker compose --profile worker build worker
  docker compose build frontend
  docker compose run --rm --no-deps backend python -c "from app.main import app; print('backend-import-ok')"
  docker compose --profile worker run --rm --no-deps worker python -c "from app.worker import celery_app; print('worker-import-ok', celery_app.main)"
  docker compose up -d postgres redis minio
  wait_for_healthy postgres 100
  wait_for_healthy redis 100
  wait_for_healthy minio 100
  docker compose run --rm minio-init
  docker compose run --rm backend alembic upgrade head
  docker compose run --rm backend alembic current
  docker compose run --rm backend alembic heads | tee /tmp/securedocs-phase-a-heads.txt
  if [[ "$(wc -l < /tmp/securedocs-phase-a-heads.txt | tr -d ' ')" != "1" ]]; then
    echo "ERROR: expected one Alembic head." >&2
    exit 1
  fi
  docker compose up -d backend frontend nginx
  wait_for_healthy backend 300
  wait_for_healthy frontend 200
  wait_for_healthy nginx 200
  docker compose exec -T nginx nginx -t
  curl -fsS http://localhost/api/v1/health >/dev/null
  curl -fsSI http://localhost/docs >/dev/null
  curl -fsS http://localhost/openapi.json >/dev/null
  curl -fsSI http://localhost/ >/dev/null
  docker compose --profile worker up -d worker
  wait_for_healthy worker 300
  docker compose --profile worker exec -T worker celery -A app.worker.celery_app inspect ping
  docker compose --profile worker exec -T worker celery -A app.worker.celery_app inspect registered | tee /tmp/securedocs-phase-a-registered.txt
  grep -q "app.extraction.extract_document_version" /tmp/securedocs-phase-a-registered.txt
  docker compose run --rm backend python -m app.scripts.enqueue_pending_extractions
  docker compose --profile test run --rm backend-test python -m pytest -q "${TARGETED_TESTS[@]}"
  if [[ -n "${SECUREDOCS_ADMIN_EMAIL:-}" && -n "${SECUREDOCS_ADMIN_PASSWORD:-}" ]]; then
    python scripts/extraction_smoke_test.py
  else
    echo "SKIP: extraction API smoke test requires SECUREDOCS_ADMIN_EMAIL and SECUREDOCS_ADMIN_PASSWORD"
  fi
}

run_python_syntax
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  run_docker_phase_a
else
  echo "WARN: Docker CLI/Compose plugin unavailable; falling back to host backend checks." >&2
  run_host_backend_tests
fi
run_frontend_checks

echo "Phase A verification completed."
