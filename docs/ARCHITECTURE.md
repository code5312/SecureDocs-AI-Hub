# SecureDocs AI Hub Architecture

## Phase A implemented flow

```mermaid
flowchart LR
  U[User upload] --> API[FastAPI documents API]
  API --> DB[(PostgreSQL metadata)]
  API --> M[MinIO original object]
  DB --> Q[Redis/Celery extraction queue]
  Q --> W[Celery worker]
  W --> DBV[Load DocumentVersion by UUID]
  DBV --> M
  M --> P[Safe parser]
  P --> C[Deterministic chunker]
  C --> CH[(document_chunks)]
```

The extraction task payload contains only `document_version_id` as a string. The worker resolves the version row, checks document deletion/status, reads the original object through DB-owned `storage_key`, extracts text, and replaces chunks idempotently in the success transaction.

## Future MVP flow

```mermaid
flowchart LR
  upload[upload] --> minio[MinIO]
  minio --> extraction[extraction queue]
  extraction --> chunk[chunk]
  chunk --> embedding[embedding queue]
  embedding --> pgvector[pgvector]
  pgvector --> acl[ACL retrieval]
  acl --> rag[RAG]
  rag --> citation[citation]
```

Phase B will add embedding providers and ACL-filtered vector search. Phase C will add RAG, classification, recommendations, comments, and backup workflows.
