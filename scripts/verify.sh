#!/usr/bin/env bash
set -euo pipefail

required=(
  APP_ENV APP_NAME API_V1_PREFIX SECRET_KEY POSTGRES_HOST POSTGRES_PORT POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD
  REDIS_URL CELERY_BROKER_URL MINIO_ENDPOINT MINIO_ACCESS_KEY MINIO_SECRET_KEY MINIO_DOCUMENT_BUCKET MINIO_PREVIEW_BUCKET
  MINIO_BACKUP_BUCKET MINIO_DATABASE_BACKUP_BUCKET EXTRACTION_MAX_FILE_SIZE_MB EXTRACTION_MAX_PAGES EXTRACTION_MAX_SLIDES EXTRACTION_MAX_SHEETS EXTRACTION_MAX_ROWS_PER_SHEET EXTRACTION_MAX_CHARACTERS EXTRACTION_MAX_CHUNKS EXTRACTION_CHUNK_SIZE EXTRACTION_CHUNK_OVERLAP EXTRACTION_MAX_ATTEMPTS CORS_ORIGINS NEXT_PUBLIC_API_BASE_URL API_INTERNAL_BASE_URL
)

if [[ ! -f .env ]]; then
  echo "ERROR: .env is missing. Run: cp .env.example .env" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

for name in "${required[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    echo "ERROR: required environment variable $name is empty or missing" >&2
    exit 1
  fi
done

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: Docker CLI is not installed; cannot run Docker Compose verification." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "ERROR: Docker Compose plugin is unavailable." >&2
  exit 1
fi

show_logs_and_exit() {
  local service="$1"
  local lines="${2:-200}"
  echo "ERROR: $service validation failed." >&2
  docker compose ps -a >&2 || true
  docker compose logs --tail="$lines" "$service" >&2 || true
  exit 1
}

wait_for_healthy() {
  local service="$1"
  local log_lines="${2:-200}"
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
  show_logs_and_exit "$service" "$log_lines"
}

assert_compose_contract() {
  docker compose --profile test --profile worker config --format json | python -c '
import json
import sys

config = json.load(sys.stdin)
services = config["services"]

assert services["backend"]["build"]["target"] == "runtime", "backend must build the runtime target"
assert services["backend-test"]["build"]["target"] == "test", "backend-test must build the test target"
assert services["worker"]["build"]["target"] == "runtime", "worker must build the runtime target"
assert "test" in services["backend-test"].get("profiles", []), "backend-test must stay behind the test profile"
assert "worker" in services["worker"].get("profiles", []), "worker must stay behind the worker profile"
for name in ("backend", "backend-test", "worker"):
    env = services[name].get("environment", {})
    assert env.get("POSTGRES_HOST") == "postgres", f"{name} must use postgres service DNS"
    assert env.get("REDIS_URL") == "redis://redis:6379/0", f"{name} must use redis service DNS"
    assert env.get("CELERY_BROKER_URL") == "redis://redis:6379/1", f"{name} must use redis broker service DNS"
    assert env.get("MINIO_ENDPOINT") == "minio:9000", f"{name} must use minio service DNS"
assert services["backend"].get("command") in (None, []), "backend must not override the runtime CMD"
backend_test_command = services["backend-test"].get("command", [])
if isinstance(backend_test_command, str):
    backend_test_command = [backend_test_command]
assert "pytest" in " ".join(backend_test_command), "backend-test must run pytest"
'
}

echo "Validating Docker Compose configuration..."
docker compose --profile test --profile worker config >/dev/null
assert_compose_contract

echo "Stopping existing containers without deleting volumes..."
docker compose --profile test --profile worker down --remove-orphans

echo "Building images..."
docker compose build backend
docker compose --profile test build backend-test
docker compose --profile worker build worker
docker compose build frontend

# Import smoke tests run before starting the full app stack so Python import failures are reported first.
docker compose run --rm --no-deps backend python -c "from app.main import app; print('backend-import-ok')"
docker compose --profile worker run --rm --no-deps worker python -c "from app.worker import celery_app; print('worker-import-ok', celery_app.main)"

docker compose up -d postgres redis minio
wait_for_healthy postgres 100
wait_for_healthy redis 100
wait_for_healthy minio 100
docker compose run --rm minio-init

docker compose run --rm backend alembic upgrade head
docker compose run --rm backend alembic current
docker compose run --rm backend alembic heads | tee /tmp/securedocs-alembic-heads.txt
if [[ "$(wc -l < /tmp/securedocs-alembic-heads.txt | tr -d ' ')" != "1" ]]; then
  echo "ERROR: expected exactly one Alembic head." >&2
  cat /tmp/securedocs-alembic-heads.txt >&2
  exit 1
fi

docker compose up -d backend
wait_for_healthy backend 300
backend_id="$(docker compose ps -q backend)"
backend_cmd="$(docker inspect "$backend_id" --format '{{json .Config.Cmd}}')"
echo "backend command: $backend_cmd"
if [[ "$backend_cmd" != *"uvicorn"* ]]; then
  show_logs_and_exit backend 300
fi
if [[ "$backend_cmd" == *"pytest"* ]]; then
  show_logs_and_exit backend 300
fi

docker compose up -d frontend
wait_for_healthy frontend 200

docker compose up -d nginx
wait_for_healthy nginx 200
docker compose exec -T nginx nginx -t

curl -fsS http://localhost/api/v1/health >/dev/null
curl -fsSI http://localhost/docs >/dev/null
curl -fsS http://localhost/openapi.json >/dev/null
curl -fsSI http://localhost/ >/dev/null

docker compose --profile worker up -d worker
wait_for_healthy worker 300
docker compose --profile worker exec -T worker celery -A app.worker.celery_app inspect ping
docker compose --profile worker exec -T worker celery -A app.worker.celery_app inspect registered | tee /tmp/securedocs-celery-registered.txt
if ! grep -q "app.extraction.extract_document_version" /tmp/securedocs-celery-registered.txt; then
  echo "ERROR: extraction task is not registered." >&2
  cat /tmp/securedocs-celery-registered.txt >&2
  exit 1
fi

docker compose run --rm backend python -m app.scripts.enqueue_pending_extractions

docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT extname FROM pg_extension WHERE extname = 'vector';"
docker compose --profile test run --rm backend-test python -m pytest -v

cd frontend
npm ci
npm run test:auth
npm run test:documents
npm run type-check
npm run lint
npm run build
