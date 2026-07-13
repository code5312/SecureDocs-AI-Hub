#!/usr/bin/env python3
"""Phase A extraction smoke test.

Creates an in-memory TXT fixture, uploads it through the public API, polls the
current version extraction status, and prints only safe metadata.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import uuid
from http import cookiejar
from urllib import error, request

API_BASE_URL = os.getenv("SECUREDOCS_API_BASE_URL", "http://localhost/api/v1").rstrip("/")
ADMIN_EMAIL = os.getenv("SECUREDOCS_ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("SECUREDOCS_ADMIN_PASSWORD")
TIMEOUT_SECONDS = int(os.getenv("SECUREDOCS_EXTRACTION_SMOKE_TIMEOUT_SECONDS", "120"))
POLL_SECONDS = float(os.getenv("SECUREDOCS_EXTRACTION_SMOKE_POLL_SECONDS", "2"))
_BODY_LIMIT = 500
_SECRET_PATTERNS = (
    re.compile(r'("?(?:access_token|refresh_token|token|password|cookie|authorization)"?\s*[:=]\s*)"?[^"\s,}]+' , re.IGNORECASE),
    re.compile(r"(Bearer\s+)[A-Za-z0-9._~+/-]+=*", re.IGNORECASE),
)


def sanitize(value: object, limit: int = _BODY_LIMIT) -> str:
    text = str(value)[:limit]
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(r"\1[REDACTED]", text)
    return text


def fail(message: str, exit_code: int = 1) -> None:
    print(f"ERROR: {sanitize(message)}", file=sys.stderr)
    raise SystemExit(exit_code)


def preflight() -> None:
    try:
        req = request.Request(f"{API_BASE_URL}/health", method="GET")
        with request.urlopen(req, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        print(f"preflight_ok api_base={API_BASE_URL} status={payload.get('status', '-')}")
    except (error.HTTPError, error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as exc:
        print(f"ERROR: API preflight failed for {API_BASE_URL}: {sanitize(exc)}", file=sys.stderr)
        print("Check that Nginx/backend are running and reachable through localhost:80.", file=sys.stderr)
        print("Suggested commands:", file=sys.stderr)
        print("  docker compose ps -a", file=sys.stderr)
        print("  docker compose logs --tail=100 nginx backend frontend", file=sys.stderr)
        raise SystemExit(1)


class ApiClient:
    def __init__(self) -> None:
        self._cookies = cookiejar.CookieJar()
        self._opener = request.build_opener(request.HTTPCookieProcessor(self._cookies))
        self._access_token: str | None = None

    def request_json(self, method: str, path: str, payload: dict | None = None) -> dict:
        body = json.dumps(payload or {}).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        req = request.Request(f"{API_BASE_URL}{path}", data=body, method=method, headers=headers)
        with self._opener.open(req, timeout=30) as response:
            data = response.read()
        return json.loads(data.decode("utf-8")) if data else {}

    def upload_txt(self, title: str, filename: str, content: bytes) -> dict:
        boundary = f"----securedocs-{uuid.uuid4().hex}"
        parts = [
            _form_part(boundary, "title", title.encode("utf-8")),
            _file_part(boundary, "file", filename, "text/plain", content),
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
        body = b"".join(parts)
        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        req = request.Request(f"{API_BASE_URL}/documents", data=body, method="POST", headers=headers)
        with self._opener.open(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))

    def login(self) -> None:
        if not ADMIN_EMAIL or not ADMIN_PASSWORD:
            fail("SECUREDOCS_ADMIN_EMAIL and SECUREDOCS_ADMIN_PASSWORD are required")
        data = self.request_json("POST", "/auth/login", {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        self._access_token = data.get("access_token")
        if not self._access_token:
            fail("login response did not include an access token")
        print(f"login_ok user_id={data.get('user', {}).get('id', '-')}")


def _form_part(boundary: str, name: str, value: bytes) -> bytes:
    return b"".join([
        f"--{boundary}\r\n".encode("utf-8"),
        f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
        value,
        b"\r\n",
    ])


def _file_part(boundary: str, name: str, filename: str, content_type: str, value: bytes) -> bytes:
    return b"".join([
        f"--{boundary}\r\n".encode("utf-8"),
        f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode("utf-8"),
        f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"),
        value,
        b"\r\n",
    ])


def main() -> None:
    preflight()
    client = ApiClient()
    try:
        client.login()
        title = f"Phase A extraction smoke {uuid.uuid4().hex[:8]}"
        document = client.upload_txt(title, "phase-a-smoke.txt", b"SecureDocs phase A smoke fixture.\n" * 80)
        document_id = document["id"]
        version = document["current_version"]
        version_id = version["id"]
        print(f"upload_ok document_id={document_id} version_id={version_id} initial_status={version.get('extraction_status')}")

        deadline = time.monotonic() + TIMEOUT_SECONDS
        last_status = version.get("extraction_status")
        if last_status not in {"PENDING", "PROCESSING", "SUCCEEDED"}:
            fail(f"unexpected initial extraction status: {last_status}")
        while time.monotonic() < deadline:
            current = client.request_json("GET", f"/documents/{document_id}")
            version = current.get("current_version") or {}
            status = version.get("extraction_status")
            if status != last_status:
                print(f"status_change document_id={document_id} version_id={version_id} status={status}")
                last_status = status
            if status == "SUCCEEDED":
                chunk_count = int(version.get("chunk_count") or 0)
                if chunk_count <= 0:
                    fail(f"extraction succeeded but chunk_count={chunk_count}")
                print(f"extraction_succeeded document_id={document_id} version_id={version_id} chunk_count={chunk_count}")
                return
            if status == "FAILED":
                print(
                    "extraction_failed "
                    f"document_id={document_id} version_id={version_id} "
                    f"error_code={sanitize(version.get('extraction_error_code'))} "
                    f"message={sanitize(version.get('extraction_error_message'), 200)}"
                )
                raise SystemExit(2)
            time.sleep(POLL_SECONDS)
        fail(f"timed out waiting for extraction status; last_status={last_status}")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        fail(f"HTTP {exc.code}: {sanitize(body)}")
    except (error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError, KeyError) as exc:
        fail(f"smoke test failed: {sanitize(exc)}")


if __name__ == "__main__":
    main()
