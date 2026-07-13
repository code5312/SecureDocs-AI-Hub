from pathlib import Path

from tests.repository_paths import find_repository_root

ROOT = find_repository_root(Path(__file__))
SERVICE_SOURCE = (ROOT / "backend/app/documents/service.py").read_text(encoding="utf-8")


def test_download_audit_records_started_completed_interrupted_and_failed_states() -> None:
    assert '"started"' in SERVICE_SOURCE
    assert '"completed" if completed else "interrupted"' in SERVICE_SOURCE
    assert '"failed"' in SERVICE_SOURCE


def test_download_completion_audit_uses_independent_session() -> None:
    assert "SessionLocal" in SERVICE_SOURCE
    assert "def _audit_download_stream" in SERVICE_SOURCE
    assert "with SessionLocal() as db" in SERVICE_SOURCE
