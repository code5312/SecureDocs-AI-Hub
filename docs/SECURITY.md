# Security Notes

## Phase A extraction controls

- Celery task payloads contain only `document_version_id` as a string.
- Storage keys are read from `DocumentVersion.storage_key` inside the worker and are not accepted from user input.
- MinIO responses are closed and released after bounded reads into a seekable temporary stream.
- TXT/Markdown reject NUL bytes; PDF encrypted documents fail safely; Office parsers do not execute macros or fetch external links; XLSX uses `read_only=True`, `data_only=True`, and `keep_links=False`.
- Worker logs and audit metadata must not contain document content, extracted text, tokens, passwords, storage keys, MinIO credentials, API keys, or stack traces.
- Queue failures are converted to safe extraction errors so document uploads are not rolled back solely because Redis is unavailable.

## Local artifact hygiene

Generated login/upload/document response files, cookies, Phase A smoke files, and TypeScript build info are ignored. Do not commit `.env`, token response JSON, cookie jars, access tokens, refresh tokens, MinIO credentials, API keys, or passwords.

## Python and validation baseline

Python 3.12 is the supported and CI-tested backend version. Docker-based backend validation is the standard Phase A path; host Python versions newer than 3.12 require separate dependency compatibility verification.
