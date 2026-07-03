from datetime import timedelta
from io import BytesIO

from minio.error import S3Error

from app.config.settings import get_settings
from app.exceptions import ErrorCode, api_error
from app.storage.minio_client import get_minio_client


class DocumentStorage:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = get_minio_client()
        self.bucket = self.settings.minio_document_bucket

    def upload(self, storage_key: str, data: bytes, mime_type: str) -> None:
        try:
            if not self.client.bucket_exists(self.bucket):
                raise api_error(503, ErrorCode.DOCUMENT_STORAGE_UNAVAILABLE, "문서 저장소 버킷이 준비되지 않았습니다.")
            self.client.put_object(self.bucket, storage_key, BytesIO(data), length=len(data), content_type=mime_type)
        except S3Error as exc:
            raise api_error(503, ErrorCode.DOCUMENT_UPLOAD_FAILED, "문서 저장 중 오류가 발생했습니다.") from exc

    def remove_uploaded_object(self, storage_key: str) -> None:
        try:
            self.client.remove_object(self.bucket, storage_key)
        except S3Error:
            return

    def presigned_download_url(self, storage_key: str) -> str:
        try:
            return self.client.presigned_get_object(self.bucket, storage_key, expires=timedelta(seconds=self.settings.document_download_url_expires_seconds))
        except S3Error as exc:
            raise api_error(503, ErrorCode.DOCUMENT_STORAGE_UNAVAILABLE, "문서 다운로드 URL을 생성할 수 없습니다.") from exc
