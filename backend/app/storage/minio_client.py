import urllib3
from minio import Minio

from app.config.settings import get_settings


def get_minio_client() -> Minio:
    """Create a MinIO client from environment-backed settings with bounded timeouts."""
    settings = get_settings()
    http_client = urllib3.PoolManager(
        timeout=urllib3.Timeout(
            connect=settings.minio_connect_timeout_seconds,
            read=settings.minio_read_timeout_seconds,
        ),
        retries=False,
    )
    return Minio(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
        http_client=http_client,
    )


def check_object_storage() -> bool:
    """Return True when every application-required MinIO bucket exists."""
    settings = get_settings()
    client = get_minio_client()
    return all(client.bucket_exists(bucket) for bucket in settings.required_minio_buckets)
