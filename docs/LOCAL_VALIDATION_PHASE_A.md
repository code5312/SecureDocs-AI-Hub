# Phase A Local Validation — Document Extraction Pipeline

Phase A covers repository audit, Celery enqueue repair, Alembic extraction metadata checks, and the asynchronous document text extraction/chunking pipeline. Phase B (embedding/vector search) must not start until these checks pass in a local Docker environment.

## Gap matrix after Phase A

| Area | Current status | Notes / next phase |
| --- | --- | --- |
| Auth, JWT access token, HttpOnly refresh token | Implemented | Regression checks remain in backend/frontend tests. |
| Users/departments/admin roles | Implemented | Existing APIs preserved. |
| Document upload/download/versioning | Implemented | Upload enqueue now happens only after DB commit. |
| ACL and SQL metadata filtering | Implemented | Future vector search must reuse `READ_CONTENT` SQL predicate. |
| Audit logs | Implemented | Extraction audit details exclude document text, storage keys, tokens, credentials, and stack traces. |
| MinIO original storage | Implemented | Extraction reads only DB-owned `DocumentVersion.storage_key`. |
| Celery/Redis extraction queue | Implemented in Phase A | `enqueue_extraction()` uses `celery_app.send_task()` with task name `app.extraction.extract_document_version`. |
| TXT/MD/PDF/DOCX/PPTX/XLSX extraction | Implemented in Phase A | No OCR, no external URL fetching, no macro execution. |
| Deterministic source-preserving chunking | Implemented in Phase A | Chunks include source locator fields and SHA-256. |
| Existing PENDING version backfill | Implemented in Phase A | `python -m app.scripts.enqueue_pending_extractions`. |
| Embeddings / pgvector search | Not implemented | Phase B. |
| RAG chat / citations | Not implemented | Phase C after Phase B validation. |
| Classification/tags/similar docs/comments/backup | Not implemented | Phase C scope. |

## Required environment

1. Copy development env values:

```bash
cp .env.example .env
```

2. Ensure the app has an admin user that can upload documents. Use the same admin email/password with the smoke test environment variables below.

3. Do not delete PostgreSQL, Redis, or MinIO volumes during validation. Avoid `docker compose down -v`.

## One-command Phase A checks

```bash
./scripts/verify_phase_a.sh
```

The script performs local Python syntax checks, targeted backend pytest checks when dependencies are installed, frontend static/type/lint/build checks when `npm` is available, and Docker Compose/Alembic/worker smoke checks when Docker CLI is available.

## Docker-backed extraction smoke test

Start dependencies and services:

```bash
docker compose up -d postgres redis minio
docker compose run --rm minio-init
docker compose run --rm backend alembic upgrade head
docker compose up -d backend
docker compose --profile worker up -d worker
```

Run a TXT upload → extraction status polling smoke test:

```bash
SECUREDOCS_API_BASE_URL=http://localhost/api/v1 \
SECUREDOCS_ADMIN_EMAIL=admin@example.com \
SECUREDOCS_ADMIN_PASSWORD='change-me' \
python scripts/extraction_smoke_test.py
```

The smoke test logs document/version identifiers, extraction status, safe error code/message, and chunk count only. It never prints access tokens, refresh tokens, MinIO credentials, storage keys, or document body text.

## Expected results

- `docker compose run --rm backend python -m app.scripts.enqueue_pending_extractions` completes without `ImportError` and prints only an enqueue count.
- `docker compose --profile worker run --rm --no-deps worker python -c "from app.worker import celery_app; print('worker-import-ok', celery_app.main)"` imports the registered worker app.
- A TXT upload transitions from `PENDING` or `PROCESSING` to `SUCCEEDED` and has `chunk_count > 0`.
- Re-running a delivered task for a `SUCCEEDED` version is a no-op and does not duplicate chunks.

## Phase B gate

Only start Phase B after sharing local results for:

```bash
./scripts/verify_phase_a.sh
SECUREDOCS_API_BASE_URL=http://localhost/api/v1 SECUREDOCS_ADMIN_EMAIL=... SECUREDOCS_ADMIN_PASSWORD=... python scripts/extraction_smoke_test.py
```
