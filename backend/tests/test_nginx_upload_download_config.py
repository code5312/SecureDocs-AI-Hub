from pathlib import Path


def test_nginx_upload_limit_matches_backend_policy() -> None:
    config = Path("../nginx/nginx.conf").read_text()

    assert "client_max_body_size 55m" in config


def test_download_location_disables_buffering_and_preserves_authorization() -> None:
    config = Path("../nginx/nginx.conf").read_text()

    assert "^/api/v1/documents/[^/]+(/versions/[^/]+)?/download$" in config
    assert "proxy_buffering off" in config
    assert "proxy_request_buffering off" in config
    assert "proxy_set_header Authorization $http_authorization" in config
