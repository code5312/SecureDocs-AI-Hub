from dataclasses import dataclass
from typing import BinaryIO, Iterator

from minio.error import S3Error

from app.config.settings import get_settings
from app.exceptions import ErrorCode, api_error
from app.storage.minio_client import get_minio_client


@dataclass(frozen=True)
class ObjectStat:
    size: int
    content_type: str | None


@dataclass(frozen=True)
class DownloadStream:
    response: object
    iterator: Iterator[bytes]


class DocumentStorage:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = get_minio_client()
        self.bucket = self.settings.minio_document_bucket

    def upload(self, storage_key: str, stream: BinaryIO, length: int, mime_type: str) -> None:
        try:
            self.ensure_bucket()
            stream.seek(0)
            self.client.put_object(self.bucket, storage_key, stream, length=length, content_type=mime_type)
        except S3Error as exc:
            raise api_error(503, ErrorCode.DOCUMENT_UPLOAD_FAILED, "문서 저장 중 오류가 발생했습니다.") from exc
        except Exception as exc:
            raise api_error(503, ErrorCode.DOCUMENT_STORAGE_UNAVAILABLE, "문서 저장소에 연결할 수 없습니다.") from exc

    def ensure_bucket(self) -> None:
        try:
            if not self.client.bucket_exists(self.bucket):
                raise api_error(503, ErrorCode.DOCUMENT_STORAGE_UNAVAILABLE, "문서 저장소 버킷이 준비되지 않았습니다.")
        except S3Error as exc:
            raise api_error(503, ErrorCode.DOCUMENT_STORAGE_UNAVAILABLE, "문서 저장소 상태를 확인할 수 없습니다.") from exc

    def remove_uploaded_object(self, storage_key: str) -> None:
        try:
            self.client.remove_object(self.bucket, storage_key)
        except S3Error:
            return

    def stat_object(self, storage_key: str) -> ObjectStat:
        try:
            self.ensure_bucket()
            stat = self.client.stat_object(self.bucket, storage_key)
            return ObjectStat(size=int(stat.size), content_type=getattr(stat, "content_type", None))
        except S3Error as exc:
            if exc.code in {"NoSuchKey", "NoSuchObject", "NoSuchBucket"}:
                raise api_error(404, ErrorCode.DOCUMENT_FILE_NOT_FOUND, "문서 원본 파일을 찾을 수 없습니다.") from exc
            raise api_error(503, ErrorCode.DOCUMENT_STORAGE_UNAVAILABLE, "문서 저장소 상태를 확인할 수 없습니다.") from exc
        except Exception as exc:
            raise api_error(503, ErrorCode.DOCUMENT_STORAGE_UNAVAILABLE, "문서 저장소에 연결할 수 없습니다.") from exc

    def open_download_stream(self, storage_key: str, chunk_size: int = 1024 * 1024) -> DownloadStream:
        try:
            response = self.client.get_object(self.bucket, storage_key)
            return DownloadStream(response=response, iterator=self.iter_response(response, chunk_size))
        except S3Error as exc:
            if exc.code in {"NoSuchKey", "NoSuchObject", "NoSuchBucket"}:
                raise api_error(404, ErrorCode.DOCUMENT_FILE_NOT_FOUND, "문서 원본 파일을 찾을 수 없습니다.") from exc
            raise api_error(503, ErrorCode.DOCUMENT_DOWNLOAD_FAILED, "문서 다운로드 스트림을 열 수 없습니다.") from exc
        except Exception as exc:
            raise api_error(503, ErrorCode.DOCUMENT_STORAGE_UNAVAILABLE, "문서 저장소에 연결할 수 없습니다.") from exc

    def iter_response(self, response: object, chunk_size: int) -> Iterator[bytes]:
        try:
            stream = getattr(response, "stream")
            yield from stream(amt=chunk_size)
        finally:
            self.close_download_stream(response)

    def close_download_stream(self, response: object) -> None:
        close = getattr(response, "close", None)
        release_conn = getattr(response, "release_conn", None)
        if callable(close):
            close()
        if callable(release_conn):
            release_conn()

    def open_original_for_extraction(self, storage_key: str, *, max_size_bytes: int, spool_max_size: int = 1024 * 1024 * 8):
        """Return a bounded seekable temp stream for a DB-owned storage key."""
        import tempfile

        stat = self.stat_object(storage_key)
        if stat.size > max_size_bytes:
            from app.extraction.errors import ExtractionError, ExtractionErrorCode
            raise ExtractionError(ExtractionErrorCode.OBJECT_TOO_LARGE)
        response = None
        temp = tempfile.SpooledTemporaryFile(max_size=spool_max_size, mode="w+b")
        downloaded = 0
        try:
            response = self.client.get_object(self.bucket, storage_key)
            for chunk in response.stream(amt=1024 * 1024):
                downloaded += len(chunk)
                if downloaded > stat.size or downloaded > max_size_bytes:
                    from app.extraction.errors import ExtractionError, ExtractionErrorCode
                    raise ExtractionError(ExtractionErrorCode.OBJECT_TOO_LARGE)
                temp.write(chunk)
            temp.seek(0)
            return temp
        except S3Error as exc:
            temp.close()
            from app.extraction.errors import ExtractionError, ExtractionErrorCode
            if exc.code in {"NoSuchKey", "NoSuchObject", "NoSuchBucket"}:
                raise ExtractionError(ExtractionErrorCode.OBJECT_NOT_FOUND) from exc
            raise ExtractionError(ExtractionErrorCode.STORAGE_UNAVAILABLE) from exc
        except Exception:
            temp.close()
            raise
        finally:
            if response is not None:
                self.close_download_stream(response)
