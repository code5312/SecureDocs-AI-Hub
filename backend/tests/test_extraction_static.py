import hashlib

import pytest

from app.extraction.chunker import chunk_segments
from app.extraction.errors import ExtractionError
from app.extraction.types import ExtractedSegment
from app.models.document_chunk import DocumentChunk
from app.models.enums import ExtractionStatus


def test_extraction_status_values():
    assert [item.value for item in ExtractionStatus] == ["PENDING", "PROCESSING", "SUCCEEDED", "FAILED"]


def test_document_chunk_has_no_storage_key_or_secret_columns():
    columns = set(DocumentChunk.__table__.columns.keys())
    assert "storage_key" not in columns
    assert "token" not in columns
    assert "password" not in columns
    assert "content" in columns


def test_chunker_deterministic_source_sha_unicode_overlap():
    segments = [ExtractedSegment(text="첫 문단입니다. " * 80, page_number=3, section_title="개요")]
    first = chunk_segments(segments, chunk_size=120, chunk_overlap=20, max_chunks=100)
    second = chunk_segments(segments, chunk_size=120, chunk_overlap=20, max_chunks=100)
    assert first == second
    assert first
    assert [chunk.chunk_index for chunk in first] == list(range(len(first)))
    assert all(chunk.content and len(chunk.content) <= 120 for chunk in first)
    assert all(chunk.page_number == 3 and chunk.section_title == "개요" for chunk in first)
    assert first[0].content_sha256 == hashlib.sha256(first[0].content.encode("utf-8")).hexdigest()


def test_chunker_max_chunks_limit():
    with pytest.raises(ExtractionError):
        chunk_segments([ExtractedSegment(text="abc " * 1000)], chunk_size=20, chunk_overlap=5, max_chunks=2)
