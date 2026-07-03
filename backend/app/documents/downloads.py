import re
from dataclasses import dataclass
from typing import Iterator
from urllib.parse import quote


@dataclass(frozen=True)
class DocumentDownload:
    filename: str
    content_type: str
    content_length: int
    stream: Iterator[bytes]


_HEADER_UNSAFE = re.compile(r'[\\/\x00-\x1f\x7f";]+')


def sanitize_download_filename(filename: str | None) -> str:
    """Return a filename safe for Content-Disposition headers."""
    cleaned = _HEADER_UNSAFE.sub("_", (filename or "document").strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ._")
    return cleaned[:180] or "document"


def content_disposition(filename: str) -> str:
    """Build an RFC 5987 Content-Disposition value without exposing storage keys."""
    safe = sanitize_download_filename(filename)
    ascii_fallback = safe.encode("ascii", "ignore").decode("ascii") or "document"
    ascii_fallback = sanitize_download_filename(ascii_fallback)
    encoded = quote(safe, safe="")
    return f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{encoded}'
