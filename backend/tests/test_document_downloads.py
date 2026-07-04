from app.documents.downloads import content_disposition, sanitize_download_filename


def test_content_disposition_uses_rfc5987_for_korean_filename() -> None:
    header = content_disposition("보안 보고서.pdf")

    assert "filename*=" in header
    assert "%EB%B3%B4%EC%95%88" in header
    assert "storage_key" not in header


def test_sanitize_download_filename_removes_header_and_path_chars() -> None:
    filename = sanitize_download_filename('../bad\r\n"name.pdf')

    assert "/" not in filename
    assert "\\" not in filename
    assert "\r" not in filename
    assert "\n" not in filename
    assert '"' not in filename
