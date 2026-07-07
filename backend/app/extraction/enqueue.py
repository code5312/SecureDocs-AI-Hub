import logging
import uuid

from celery.exceptions import CeleryError
from kombu.exceptions import KombuError

from app.extraction.errors import ExtractionError, ExtractionErrorCode

TASK_NAME = "app.extraction.extract_document_version"

logger = logging.getLogger(__name__)


def enqueue_extraction(document_version_id: uuid.UUID) -> None:
    """Enqueue extraction using only the version UUID payload.

    Import the Celery app lazily and use the stable task name instead of importing
    the dynamically registered task object. This keeps backfill scripts free of
    task-object import errors and avoids passing storage keys or document text.
    """
    payload = str(document_version_id)
    try:
        from app.worker import celery_app

        celery_app.send_task(TASK_NAME, args=[payload])
    except (CeleryError, KombuError, OSError, RuntimeError) as exc:
        logger.warning("document extraction enqueue failed version_id=%s", document_version_id)
        raise ExtractionError(ExtractionErrorCode.QUEUE_UNAVAILABLE) from exc
