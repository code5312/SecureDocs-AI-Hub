# SecureDocs AI Hub API Notes

## Phase A extraction endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/documents` | Upload document and enqueue extraction after commit. |
| `POST` | `/api/v1/documents/{document_id}/versions` | Upload a new version and enqueue extraction after commit. |
| `GET` | `/api/v1/documents/{document_id}` | Returns current version extraction metadata. |
| `GET` | `/api/v1/documents/{document_id}/versions` | Returns all version extraction metadata. |
| `POST` | `/api/v1/documents/{document_id}/versions/{version_id}/extraction/retry` | Retry a `FAILED` or `PENDING` extraction if the caller can upload versions. |

`DocumentVersionRead` includes `extraction_status`, `extraction_error_code`, `extraction_error_message`, `extraction_attempts`, `extracted_at`, and `chunk_count`. Chunk content is not exposed by a public API in Phase A.

## Backfill command

```bash
docker compose run --rm backend python -m app.scripts.enqueue_pending_extractions
```

The command prints only the number of enqueued versions.
