# Phase A Local Validation — Document Extraction Pipeline

Phase A covers Celery enqueue/runtime validation, Alembic extraction metadata checks, and the asynchronous document text extraction/chunking pipeline. Phase B/C work (embedding, pgvector, RAG, classification, recommendations, comments, backup) must not start until this local gate passes.

## Current implementation matrix

| Area | Status | Notes |
| --- | --- | --- |
| Auth, users, departments, roles | Implemented | JWT access token and HttpOnly refresh cookie are already part of the app. |
| Documents, versions, ACL, audit logs | Implemented | Keep backend authorization as the security boundary. |
| MinIO original storage | Implemented | Storage keys remain DB-owned and are not accepted from API/task payloads. |
| Celery/Redis extraction queue | Phase A implemented | Enqueue uses `celery_app.send_task("app.extraction.extract_document_version", args=[version_id])`. |
| TXT/MD/PDF/DOCX/PPTX/XLSX extraction | Phase A implemented | No OCR, no macro execution, no external URL fetching. |
| Deterministic source-preserving chunking | Phase A implemented | Chunk content is internal and not exposed through public API. |
| PENDING backfill | Phase A implemented | `python -m app.scripts.enqueue_pending_extractions`. |
| Embedding, vector search, RAG | Not implemented | Phase B/C only. |

## Runtime contract

- External HTTP entrypoint: `http://localhost` through Nginx.
- Docker service DNS inside Compose: `postgres`, `redis`, `minio`.
- Backend/worker/test container paths: `WORKDIR=/workspace/backend`.
- Host repository root test path: `backend/tests/test_extraction_static.py`.
- After `cd backend`, and inside `backend-test`, pytest arguments use `tests/test_extraction_static.py`.
- Python support target: Python 3.12. Docker backend validation is the standard path; other Python versions need explicit compatibility verification.

## Canonical one-command validation

Run from the repository root:

```bash
bash scripts/verify_phase_a.sh
```

The script performs Python syntax checks, Docker Compose config validation, image builds, backend/worker imports, dependency startup, Alembic head checks, Nginx/API health checks, worker ping and registered-task checks, PENDING backfill import/runtime check, targeted backend tests, and frontend tests/type-check/lint/build.

If Docker is unavailable, the script does not silently pass core Phase A validation. It falls back only to host checks that can actually run and exits with a clear error when required dependencies are missing.

## Targeted backend tests

Host path from repository root:

```bash
backend/tests/test_extraction_static.py
backend/tests/test_extraction_enqueue.py
backend/tests/test_document_versions_static.py
backend/tests/test_document_acl_static.py
```

Host after `cd backend`:

```bash
python -m pytest -q \
  tests/test_extraction_static.py \
  tests/test_extraction_enqueue.py \
  tests/test_document_versions_static.py \
  tests/test_document_acl_static.py
```

Docker `backend-test`:

```bash
docker compose --profile test run --rm backend-test \
  python -m pytest -q \
  tests/test_extraction_static.py \
  tests/test_extraction_enqueue.py \
  tests/test_document_versions_static.py \
  tests/test_document_acl_static.py
```

Do not use `backend/tests/...` as a pytest argument inside the `backend-test` container.

## Optional authenticated extraction smoke test

The smoke test runs only when credentials are explicitly provided:

```bash
SECUREDOCS_API_BASE_URL=http://localhost/api/v1 \
SECUREDOCS_ADMIN_EMAIL=admin@example.com \
SECUREDOCS_ADMIN_PASSWORD='change-me' \
python scripts/extraction_smoke_test.py
```

Without `SECUREDOCS_ADMIN_EMAIL` and `SECUREDOCS_ADMIN_PASSWORD`, `scripts/verify_phase_a.sh` prints:

```text
SKIP: extraction API smoke test requires SECUREDOCS_ADMIN_EMAIL and SECUREDOCS_ADMIN_PASSWORD
```

The smoke test performs API preflight, login, TXT upload, extraction polling, and `chunk_count > 0` validation. It does not print passwords, access tokens, refresh tokens, cookies, storage keys, or document content.

## Frontend dependency security note

Update `next` and `eslint-config-next` together to a compatible patched release, then regenerate `frontend/package-lock.json` with `npm install`/`npm ci` in an environment that can access the npm registry. Do not use `npm audit fix --force`. Record `npm audit` results separately from this validation gate.
