from pathlib import Path

from tests.repository_paths import find_repository_root

ROOT = find_repository_root(Path(__file__))


def test_nginx_upload_limit_matches_backend_policy() -> None:
    config = (ROOT / "nginx" / "nginx.conf").read_text()

    assert "client_max_body_size 55m" in config


def test_download_location_disables_buffering_and_preserves_authorization() -> None:
    config = (ROOT / "nginx" / "nginx.conf").read_text()

    assert "^/api/v1/documents/[^/]+(/versions/[^/]+)?/download$" in config
    assert "proxy_buffering off" in config
    assert "proxy_request_buffering off" in config
    assert "proxy_set_header Authorization $http_authorization" in config
