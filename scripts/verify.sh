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

docker compose config
docker compose build
docker compose up -d

echo "Waiting for health endpoint..."
for _ in {1..30}; do
  if curl -fsS http://localhost/api/v1/health >/tmp/securedocs-health.json; then
    cat /tmp/securedocs-health.json
    break
  fi
  sleep 2
done

curl -fsS http://localhost/api/v1/health >/dev/null
curl -fsSI http://localhost/docs >/dev/null
curl -fsS http://localhost/openapi.json >/dev/null
curl -fsSI http://localhost/ >/dev/null

docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT extname FROM pg_extension WHERE extname = 'vector';"
docker compose exec -T backend alembic upgrade head
docker compose run --rm minio-init
cd backend
python -m pytest
cd ../frontend
npm ci
npm run type-check
npm run lint
npm run build
