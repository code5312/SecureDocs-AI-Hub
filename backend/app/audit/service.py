from sqlalchemy.orm import Session

from app.audit.repository import AuditRepository
from app.models.enums import AuditAction

SENSITIVE_KEYS = {"password", "password_hash", "access_token", "refresh_token", "token", "storage_key", "presigned_url", "url"}


def sanitize_details(details: dict | None) -> dict | None:
    if details is None:
        return None
    return {key: value for key, value in details.items() if key not in SENSITIVE_KEYS}


class AuditService:
    def __init__(self, db: Session) -> None:
        self.repository = AuditRepository(db)

    def record(self, *, action: AuditAction, actor_id=None, target_type: str | None = None, target_id: str | None = None, ip_address: str | None = None, user_agent: str | None = None, details: dict | None = None) -> None:
        self.repository.create(action=action, actor_id=actor_id, target_type=target_type, target_id=target_id, ip_address=ip_address, user_agent=user_agent, details=sanitize_details(details))
