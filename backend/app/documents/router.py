import uuid

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.database.session import get_db
from app.dependencies.auth import get_current_user, request_ip
from app.documents.schemas import DocumentRead, DocumentVersionRead, DownloadUrlResponse
from app.documents.service import DocumentService
from app.models.enums import DocumentStatus
from app.models.user import User

router = APIRouter(prefix="/documents", tags=["documents"])


def _read_document(document) -> DocumentRead:
    version = next((item for item in document.versions if item.id == document.current_version_id), None)
    payload = DocumentRead.model_validate(document)
    payload.current_version = DocumentVersionRead.model_validate(version) if version else None
    return payload


@router.post("", response_model=DocumentRead, status_code=201)
async def upload_document(request: Request, title: str = Form(...), description: str | None = Form(None), file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DocumentRead:
    data = await file.read()
    document = DocumentService(db).upload(title=title, description=description, filename=file.filename or "upload", content_type=file.content_type, data=data, actor=current_user, ip_address=request_ip(request), user_agent=request.headers.get("user-agent"))
    return _read_document(document)


@router.get("", response_model=list[DocumentRead])
def list_documents(current_user: User = Depends(get_current_user), db: Session = Depends(get_db), offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), title: str | None = None, owner_id: uuid.UUID | None = None, department_id: uuid.UUID | None = None, status: DocumentStatus | None = None) -> list[DocumentRead]:
    documents = DocumentService(db).list_documents(current_user, offset=offset, limit=limit, title=title, owner_id=owner_id, department_id=department_id, status=status)
    return [_read_document(document) for document in documents]


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DocumentRead:
    return _read_document(DocumentService(db).get_document(current_user, document_id))


@router.get("/{document_id}/download", response_model=DownloadUrlResponse)
def download_document(document_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DownloadUrlResponse:
    url = DocumentService(db).download(current_user, document_id)
    return DownloadUrlResponse(url=url, expires_in=get_settings().document_download_url_expires_seconds)


@router.delete("/{document_id}", response_model=DocumentRead)
def delete_document(document_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DocumentRead:
    return _read_document(DocumentService(db).delete(current_user, document_id))
