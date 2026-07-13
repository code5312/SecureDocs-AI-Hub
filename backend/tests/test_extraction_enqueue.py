import uuid

import pytest

from app.extraction import enqueue as enqueue_module
from app.extraction.errors import ExtractionError, ExtractionErrorCode
from app.extraction.enqueue import TASK_NAME, enqueue_extraction
from app.worker import celery_app


class RecordingCeleryApp:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[str]]] = []

    def send_task(self, name: str, args: list[str]) -> None:
        self.calls.append((name, args))


class FailingCeleryApp:
    def send_task(self, name: str, args: list[str]) -> None:
        raise OSError("broker unavailable")


def test_extraction_task_registered_on_worker_app() -> None:
    assert TASK_NAME in celery_app.tasks


def test_enqueue_uses_uuid_string_payload_only(monkeypatch: pytest.MonkeyPatch) -> None:
    version_id = uuid.uuid4()
    recorder = RecordingCeleryApp()
    monkeypatch.setattr(enqueue_module, "celery_app", recorder, raising=False)
    monkeypatch.setitem(__import__("sys").modules, "app.worker", type("WorkerModule", (), {"celery_app": recorder}))

    enqueue_extraction(version_id)

    assert recorder.calls == [(TASK_NAME, [str(version_id)])]


def test_enqueue_import_path_does_not_require_task_global() -> None:
    import app.extraction.tasks as tasks

    assert hasattr(tasks, "register_tasks")
    assert not hasattr(tasks, "extract_document_version")


def test_enqueue_queue_failure_is_safe_domain_error(monkeypatch: pytest.MonkeyPatch) -> None:
    failing = FailingCeleryApp()
    monkeypatch.setitem(__import__("sys").modules, "app.worker", type("WorkerModule", (), {"celery_app": failing}))

    with pytest.raises(ExtractionError) as caught:
        enqueue_extraction(uuid.uuid4())

    assert caught.value.code == ExtractionErrorCode.QUEUE_UNAVAILABLE
