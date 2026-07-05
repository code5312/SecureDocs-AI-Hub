#!/usr/bin/env bash
set -euo pipefail

required=(
  APP_ENV APP_NAME API_V1_PREFIX SECRET_KEY POSTGRES_HOST POSTGRES_PORT POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD
  REDIS_URL MINIO_ENDPOINT MINIO_ACCESS_KEY MINIO_SECRET_KEY MINIO_DOCUMENT_BUCKET MINIO_PREVIEW_BUCKET
  MINIO_BACKUP_BUCKET MINIO_DATABASE_BACKUP_BUCKET CORS_ORIGINS NEXT_PUBLIC_API_BASE_URL API_INTERNAL_BASE_URL
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

wait_for_healthy() {
  local service="$1"
  local log_lines="${2:-200}"
  echo "Waiting for $service to become healthy..."
  for _ in {1..40}; do
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
  docker compose ps -a >&2
  docker compose logs --tail="$log_lines" "$service" >&2
  exit 1
}

echo "Validating Docker Compose configuration..."
docker compose config
docker compose config --format json | python -c '
import json
import sys

config = json.load(sys.stdin)
services = config["services"]

assert services["backend"]["build"]["target"] == "runtime", "backend must build the runtime target"
assert services["backend-test"]["build"]["target"] == "test", "backend-test must build the test target"
assert services["worker"]["build"]["target"] == "runtime", "worker must build the runtime target"
assert "test" in services["backend-test"].get("profiles", []), "backend-test must stay behind the test profile"
assert services["backend"].get("command") in (None, []), "backend must not override the runtime CMD"
backend_test_command = services["backend-test"].get("command", [])
if isinstance(backend_test_command, str):
    backend_test_command = [backend_test_command]
assert "pytest" in " ".join(backend_test_command), "backend-test must run pytest"
'

docker compose build backend
docker compose --profile test build backend-test
docker compose build frontend

# Import smoke test runs before starting the full app stack so Python import failures are reported first.
docker compose run --rm --no-deps backend python -c "from app.main import app; print('backend-import-ok')"

docker compose up -d postgres redis minio
wait_for_healthy postgres 100
wait_for_healthy redis 100
wait_for_healthy minio 100
docker compose run --rm minio-init

docker compose run --rm backend alembic upgrade head
docker compose run --rm backend alembic current
docker compose run --rm backend alembic heads

docker compose up -d backend
wait_for_healthy backend 300
backend_id="$(docker compose ps -q backend)"
backend_cmd="$(docker inspect "$backend_id" --format '{{json .Config.Cmd}}')"
echo "backend command: $backend_cmd"
if [[ "$backend_cmd" != *"uvicorn"* ]]; then
  echo "ERROR: backend is not using the runtime uvicorn command: $backend_cmd" >&2
  docker compose logs --tail=300 backend >&2
  exit 1
fi
if [[ "$backend_cmd" == *"pytest"* ]]; then
  echo "ERROR: backend is incorrectly using the test command: $backend_cmd" >&2
  docker compose logs --tail=300 backend >&2
  exit 1
fi

curl -fsS http://localhost/api/v1/health >/dev/null
curl -fsSI http://localhost/docs >/dev/null
curl -fsS http://localhost/openapi.json >/dev/null

docker compose up -d frontend
wait_for_healthy frontend 200
curl -fsSI http://localhost/ >/dev/null

docker compose up -d nginx
wait_for_healthy nginx 200
docker compose exec -T nginx nginx -t

docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT extname FROM pg_extension WHERE extname = 'vector';"
docker compose --profile test run --rm backend-test python -m pytest -v
cd frontend
npm ci
npm run test:auth
npm run test:documents
npm run type-check
npm run lint
npm run build
