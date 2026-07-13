import uuid

from app.database.session import SessionLocal


def run_extraction(document_version_id: str) -> None:
    from app.extraction.service import DocumentExtractionService

    with SessionLocal() as db:
        DocumentExtractionService(db).process_version(uuid.UUID(document_version_id))


def register_tasks(celery_app):
    @celery_app.task(name="app.extraction.extract_document_version")
    def extract_document_version(document_version_id: str) -> None:
        run_extraction(document_version_id)

    return extract_document_version
