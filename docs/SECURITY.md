# SecureDocs AI Hub Security Notes

## Phase A extraction controls

- Document extraction reads MinIO objects only through `DocumentVersion.storage_key` loaded from the database.
- API requests and Celery payloads never accept storage keys, filesystem paths, document text, JWTs, passwords, MinIO credentials, or LLM API keys.
- TXT/Markdown extraction rejects NUL bytes and uses UTF-8/UTF-8-SIG only.
- PDF extraction rejects encrypted PDFs and does not perform OCR.
- Office extraction uses Python libraries only; no LibreOffice, shell conversion, macro execution, or external URL fetching is used.
- XLSX extraction uses `read_only=True`, `data_only=True`, and `keep_links=False`.
- MinIO responses are closed and released after bounded streaming into a `SpooledTemporaryFile`.
- Worker logs and audit logs include document/version identifiers, status, error code, attempts, and chunk count only.

## Phase B/C security gates

- Vector search must filter by backend-calculated `READ_CONTENT` access scope in SQL before chunks can reach a model provider.
- RAG answers must include citations and must not treat document content as system/developer instructions.
- Destructive restore remains out of scope unless explicitly enabled by configuration.
