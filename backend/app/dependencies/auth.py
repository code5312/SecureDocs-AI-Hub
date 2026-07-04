import uuid

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.database.session import get_db
from app.exceptions import ErrorCode, api_error, forbidden
from app.models.enums import UserRole
from app.models.user import User
from app.users.repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme), db: Session = Depends(get_db)) -> User:
    if credentials is None:
        raise api_error(401, ErrorCode.AUTH_INVALID_TOKEN, "인증이 필요합니다.")
    payload = decode_access_token(credentials.credentials)
    user_id = uuid.UUID(str(payload["sub"]))
    user = UserRepository(db).get_by_id(user_id)
    if user is None:
        raise api_error(401, ErrorCode.AUTH_INVALID_TOKEN, "유효하지 않은 토큰입니다.")
    if not user.is_active:
        raise api_error(403, ErrorCode.AUTH_INACTIVE_USER, "비활성 사용자입니다.")
    return user


def require_system_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.SYSTEM_ADMIN:
        raise forbidden()
    return current_user


def request_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    return forwarded.split(",")[0].strip() if forwarded else request.client.host if request.client else None
