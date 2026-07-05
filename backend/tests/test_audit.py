from app.audit.service import sanitize_details


def test_audit_details_strip_sensitive_values() -> None:
    sanitized = sanitize_details({"password": "secret", "access_token": "token", "refresh_token": "token", "email": "user@example.com"})

    assert sanitized == {"email": "user@example.com"}
