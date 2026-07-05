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

docker compose build
docker compose --profile test build backend-test
docker compose up -d

echo "Waiting for health endpoint..."
for _ in {1..30}; do
  if curl -fsS http://localhost/api/v1/health >/tmp/securedocs-health.json; then
    cat /tmp/securedocs-health.json
    break
  fi
  sleep 2
done

backend_id="$(docker compose ps -q backend)"
if [[ -z "$backend_id" ]]; then
  echo "ERROR: backend container is not running." >&2
  docker compose ps -a >&2
  exit 1
fi
backend_cmd="$(docker inspect "$backend_id" --format '{{json .Config.Cmd}}')"
echo "backend command: $backend_cmd"
if [[ "$backend_cmd" != *"uvicorn"* ]]; then
  echo "ERROR: backend is not using the runtime uvicorn command: $backend_cmd" >&2
  docker compose logs --tail=100 backend >&2
  exit 1
fi
if [[ "$backend_cmd" == *"pytest"* ]]; then
  echo "ERROR: backend is incorrectly using the test command: $backend_cmd" >&2
  docker compose logs --tail=100 backend >&2
  exit 1
fi

docker compose ps -a
docker compose logs --tail=100 backend

curl -fsS http://localhost/api/v1/health >/dev/null
curl -fsSI http://localhost/docs >/dev/null
curl -fsS http://localhost/openapi.json >/dev/null
curl -fsSI http://localhost/ >/dev/null

docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT extname FROM pg_extension WHERE extname = 'vector';"
docker compose exec -T backend alembic upgrade head
docker compose run --rm minio-init
docker compose --profile test run --rm backend-test python -m pytest -v
cd frontend
npm ci
npm run test:auth
npm run test:documents
npm run type-check
npm run lint
npm run build
