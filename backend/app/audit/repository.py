from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.enums import AuditAction


class AuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, action: AuditAction, actor_id=None, target_type: str | None = None, target_id: str | None = None, ip_address: str | None = None, user_agent: str | None = None, details: dict | None = None) -> AuditLog:
        log = AuditLog(action=action, actor_id=actor_id, target_type=target_type, target_id=target_id, ip_address=ip_address, user_agent=user_agent, details=details)
        self.db.add(log)
        return log
