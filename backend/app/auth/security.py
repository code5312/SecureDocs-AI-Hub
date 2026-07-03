import hashlib
import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config.settings import get_settings
from app.exceptions import ErrorCode, api_error

_password_hasher = PasswordHasher()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_password_policy(password: str, email: str) -> str:
    value = password.strip()
    if len(value) < 10 or len(value) > 128:
        raise api_error(422, ErrorCode.VALIDATION_ERROR, "비밀번호는 10자 이상 128자 이하로 입력하세요.")
    if normalize_email(email) == value.lower():
        raise api_error(422, ErrorCode.VALIDATION_ERROR, "비밀번호는 이메일과 같을 수 없습니다.")
    checks = [r"[A-Z]", r"[a-z]", r"[0-9]", r"[^A-Za-z0-9]"]
    if not all(re.search(pattern, value) for pattern in checks):
        raise api_error(422, ErrorCode.VALIDATION_ERROR, "비밀번호는 대/소문자, 숫자, 특수문자를 포함해야 합니다.")
    return value


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def create_access_token(user_id: uuid.UUID, role: str) -> tuple[str, int]:
    settings = get_settings()
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    expires_at = datetime.now(UTC) + expires_delta
    payload: dict[str, Any] = {"sub": str(user_id), "role": role, "typ": "access", "exp": expires_at}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm), int(expires_delta.total_seconds())


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise api_error(401, ErrorCode.AUTH_EXPIRED_TOKEN, "Access Token이 만료되었습니다.") from exc
    except jwt.PyJWTError as exc:
        raise api_error(401, ErrorCode.AUTH_INVALID_TOKEN, "유효하지 않은 토큰입니다.") from exc
    if payload.get("typ") != "access":
        raise api_error(401, ErrorCode.AUTH_INVALID_TOKEN, "토큰 타입이 올바르지 않습니다.")
    return payload


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
