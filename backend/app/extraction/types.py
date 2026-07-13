from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractedSegment:
    text: str
    page_number: int | None = None
    slide_number: int | None = None
    sheet_name: str | None = None
    row_start: int | None = None
    row_end: int | None = None
    section_title: str | None = None


@dataclass(frozen=True)
class ChunkCandidate:
    chunk_index: int
    content: str
    content_sha256: str
    character_count: int
    page_number: int | None = None
    slide_number: int | None = None
    sheet_name: str | None = None
    row_start: int | None = None
    row_end: int | None = None
    section_title: str | None = None
