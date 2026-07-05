import hashlib

from app.extraction.errors import ExtractionError, ExtractionErrorCode
from app.extraction.types import ChunkCandidate, ExtractedSegment


def _split_text(text: str, size: int, overlap: int) -> list[str]:
    pieces: list[str] = []
    cursor = 0
    while cursor < len(text):
        limit = min(cursor + size, len(text))
        end = limit
        if limit < len(text):
            window = text[cursor:limit]
            candidates = [window.rfind("\n\n"), window.rfind("\n"), window.rfind(" ")]
            boundary = max(c for c in candidates if c > max(0, size // 2)) if any(c > max(0, size // 2) for c in candidates) else -1
            if boundary > 0:
                end = cursor + boundary
        chunk = text[cursor:end].strip()
        if chunk:
            pieces.append(chunk)
        if end >= len(text):
            break
        cursor = max(end - overlap, cursor + 1)
    return pieces


def chunk_segments(segments: list[ExtractedSegment], *, chunk_size: int, chunk_overlap: int, max_chunks: int) -> list[ChunkCandidate]:
    """Create deterministic source-preserving chunks from extracted segments."""
    chunks: list[ChunkCandidate] = []
    for segment in segments:
        text = "\n".join(line.rstrip() for line in segment.text.replace("\r\n", "\n").replace("\r", "\n").split("\n")).strip()
        if not text:
            continue
        for piece in _split_text(text, chunk_size, chunk_overlap):
            if len(chunks) >= max_chunks:
                raise ExtractionError(ExtractionErrorCode.CHUNK_LIMIT_EXCEEDED)
            chunks.append(ChunkCandidate(chunk_index=len(chunks), content=piece, content_sha256=hashlib.sha256(piece.encode("utf-8")).hexdigest(), character_count=len(piece), page_number=segment.page_number, slide_number=segment.slide_number, sheet_name=segment.sheet_name, row_start=segment.row_start, row_end=segment.row_end, section_title=segment.section_title))
    return chunks
