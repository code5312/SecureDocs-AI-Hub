from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.auth.security import create_access_token, decode_access_token, hash_refresh_token, normalize_email, validate_password_policy
from app.config.settings import get_settings
from app.exceptions.errors import ErrorCode
from app.models.enums import UserRole


def test_normalize_email_trims_and_lowercases() -> None:
    assert normalize_email(" Admin@Example.COM ") == "admin@example.com"


def test_password_policy_accepts_strong_password() -> None:
    assert validate_password_policy(" ExamplePassword1! ", "admin@example.com") == "ExamplePassword1!"


@pytest.mark.parametrize("password", ["short1!A", "lowercase1!", "UPPERCASE1!", "NoNumber!!", "NoSpecial11"])
def test_password_policy_rejects_weak_password(password: str) -> None:
    with pytest.raises(Exception):
        validate_password_policy(password, "admin@example.com")


def test_password_policy_rejects_email_as_password() -> None:
    with pytest.raises(Exception):
        validate_password_policy("admin@example.com", "admin@example.com")


def test_access_token_create_and_decode() -> None:
    import uuid
    user_id = uuid.uuid4()
    token, expires_in = create_access_token(user_id, UserRole.SYSTEM_ADMIN.value)

    payload = decode_access_token(token)

    assert expires_in > 0
    assert payload["sub"] == str(user_id)
    assert payload["role"] == UserRole.SYSTEM_ADMIN.value
    assert payload["typ"] == "access"


def test_expired_access_token_is_rejected() -> None:
    settings = get_settings()
    token = jwt.encode({"sub": "00000000-0000-0000-0000-000000000000", "typ": "access", "exp": datetime.now(UTC) - timedelta(seconds=1)}, settings.secret_key, algorithm=settings.jwt_algorithm)

    with pytest.raises(Exception) as exc_info:
        decode_access_token(token)

    assert ErrorCode.AUTH_EXPIRED_TOKEN in str(exc_info.value)


def test_refresh_token_hash_does_not_store_plain_token() -> None:
    token = "refresh-token-value"

    digest = hash_refresh_token(token)

    assert digest != token
    assert len(digest) == 64
