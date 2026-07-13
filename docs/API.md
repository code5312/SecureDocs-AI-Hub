# API Notes

## Phase A extraction endpoints

### Retry extraction

```text
POST /api/v1/documents/{document_id}/versions/{version_id}/extraction/retry
```

Allowed callers are the document owner, `SYSTEM_ADMIN`, or users with the existing `UPLOAD_VERSION` permission. Deleted documents are rejected. `PROCESSING` and `SUCCEEDED` versions return conflict responses; `FAILED` and `PENDING` versions can be reset to `PENDING` and re-enqueued.

`DocumentVersionRead` includes `extraction_status`, `extraction_error_code`, `extraction_error_message`, `extraction_attempts`, `extracted_at`, and `chunk_count`. Chunk content is not exposed by a public API in Phase A.

## External entrypoint

Local HTTP access should use Nginx:

```text
http://localhost/api/v1/health
http://localhost/docs
http://localhost/openapi.json
```

Backend and frontend container ports are not published to the host in the standard Compose contract.
