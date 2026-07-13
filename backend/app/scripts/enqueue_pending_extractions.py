from sqlalchemy import select

from app.database.session import SessionLocal
from app.extraction.enqueue import enqueue_extraction
from app.models.document import Document, DocumentVersion
from app.models.enums import ExtractionStatus

BATCH_LIMIT = 100


def main() -> None:
    enqueued = 0
    with SessionLocal() as db:
        stmt = select(DocumentVersion.id).join(Document, DocumentVersion.document_id == Document.id).where(Document.is_deleted.is_(False), DocumentVersion.extraction_status == ExtractionStatus.PENDING).order_by(DocumentVersion.created_at.asc()).limit(BATCH_LIMIT)
        for version_id in db.scalars(stmt):
            enqueue_extraction(version_id)
            enqueued += 1
    print(f"enqueued_pending_extractions={enqueued}")


if __name__ == "__main__":
    main()
