import logging
import uuid

from kombu.exceptions import KombuError

from app.extraction.errors import ExtractionError, ExtractionErrorCode

logger = logging.getLogger(__name__)


def enqueue_extraction(document_version_id: uuid.UUID) -> None:
    """Enqueue extraction using only the version UUID payload."""
    try:
        from app.extraction.tasks import extract_document_version

        extract_document_version.delay(str(document_version_id))
    except (KombuError, OSError, RuntimeError) as exc:
        logger.warning("document extraction enqueue failed version_id=%s", document_version_id)
        raise ExtractionError(ExtractionErrorCode.QUEUE_UNAVAILABLE) from exc
