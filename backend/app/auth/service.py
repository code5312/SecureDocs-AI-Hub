import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.auth.repository import RefreshTokenRepository
from app.auth.security import create_access_token, generate_refresh_token, hash_refresh_token, verify_password
from app.config.settings import get_settings
from app.exceptions import ErrorCode, api_error
from app.models.auth import RefreshToken
from app.models.enums import AuditAction
from app.models.user import User
from app.users.repository import UserRepository


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.tokens = RefreshTokenRepository(db)
        self.audit = AuditService(db)

    def login(self, *, email: str, password: str, ip_address: str | None, user_agent: str | None) -> tuple[str, int, str, User]:
        user = self.users.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            self.audit.record(action=AuditAction.LOGIN_FAILED, target_type="User", ip_address=ip_address, user_agent=user_agent, details={"email": email})
            raise api_error(401, ErrorCode.AUTH_INVALID_CREDENTIALS, "이메일 또는 비밀번호가 올바르지 않습니다.")
        if not user.is_active:
            self.audit.record(action=AuditAction.LOGIN_FAILED, actor_id=user.id, target_type="User", target_id=str(user.id), ip_address=ip_address, user_agent=user_agent, details={"reason": "inactive"})
            raise api_error(403, ErrorCode.AUTH_INACTIVE_USER, "비활성 사용자입니다.")
        user.last_login_at = datetime.now(UTC)
        access_token, expires_in = create_access_token(user.id, user.role.value)
        refresh_token = self._create_refresh_token(user, ip_address, user_agent)
        self.audit.record(action=AuditAction.LOGIN_SUCCESS, actor_id=user.id, target_type="User", target_id=str(user.id), ip_address=ip_address, user_agent=user_agent)
        self.db.commit()
        self.db.refresh(user)
        return access_token, expires_in, refresh_token, user

    def refresh(self, *, raw_refresh_token: str | None, ip_address: str | None, user_agent: str | None) -> tuple[str, int, str, User]:
        if not raw_refresh_token:
            raise api_error(401, ErrorCode.AUTH_REFRESH_TOKEN_REQUIRED, "Refresh Token이 필요합니다.")
        stored = self.tokens.get_active_by_hash(hash_refresh_token(raw_refresh_token))
        if stored is None:
            raise api_error(401, ErrorCode.AUTH_REFRESH_TOKEN_REVOKED, "Refresh Token이 유효하지 않습니다.")
        if stored.expires_at <= datetime.now(UTC):
            self.tokens.revoke(stored)
            self.db.commit()
            raise api_error(401, ErrorCode.AUTH_EXPIRED_TOKEN, "Refresh Token이 만료되었습니다.")
        user = self.users.get_by_id(stored.user_id)
        if user is None or not user.is_active:
            raise api_error(403, ErrorCode.AUTH_INACTIVE_USER, "비활성 사용자입니다.")
        self.tokens.revoke(stored)
        access_token, expires_in = create_access_token(user.id, user.role.value)
        new_refresh_token = self._create_refresh_token(user, ip_address, user_agent)
        self.audit.record(action=AuditAction.TOKEN_REFRESH, actor_id=user.id, target_type="RefreshToken", target_id=str(stored.id), ip_address=ip_address, user_agent=user_agent)
        self.db.commit()
        return access_token, expires_in, new_refresh_token, user

    def logout(self, *, raw_refresh_token: str | None, ip_address: str | None, user_agent: str | None) -> None:
        if raw_refresh_token:
            stored = self.tokens.get_active_by_hash(hash_refresh_token(raw_refresh_token))
            if stored is not None:
                self.tokens.revoke(stored)
                self.audit.record(action=AuditAction.LOGOUT, actor_id=stored.user_id, target_type="RefreshToken", target_id=str(stored.id), ip_address=ip_address, user_agent=user_agent)
        self.db.commit()

    def _create_refresh_token(self, user: User, ip_address: str | None, user_agent: str | None) -> str:
        settings = get_settings()
        raw = generate_refresh_token()
        stored = RefreshToken(user_id=user.id, token_hash=hash_refresh_token(raw), expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days), ip_address=ip_address, user_agent=user_agent)
        self.tokens.create(stored)
        return raw
