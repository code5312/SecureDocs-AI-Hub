import uuid

from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.auth.security import hash_password, normalize_email, validate_password_policy
from app.departments.repository import DepartmentRepository
from app.exceptions import ErrorCode, api_error, forbidden
from app.models.enums import AuditAction, UserRole
from app.models.user import User
from app.users.repository import UserRepository
from app.users.schemas import UserCreate, UserUpdate


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.departments = DepartmentRepository(db)
        self.audit = AuditService(db)

    def list_users(self, current_user: User, *, offset: int, limit: int, email: str | None, name: str | None, role: UserRole | None, department_id: uuid.UUID | None, is_active: bool | None) -> list[User]:
        if current_user.role == UserRole.SYSTEM_ADMIN:
            return self.users.list(offset=offset, limit=limit, email=email, name=name, role=role, department_id=department_id, is_active=is_active)
        if current_user.role == UserRole.DEPARTMENT_MANAGER and current_user.department_id:
            return self.users.list(offset=offset, limit=limit, email=email, name=name, role=role, department_id=current_user.department_id, is_active=is_active)
        raise forbidden()

    def get_visible_user(self, current_user: User, user_id: uuid.UUID) -> User:
        target = self.users.get_by_id(user_id)
        if target is None:
            raise api_error(404, ErrorCode.USER_NOT_FOUND, "사용자를 찾을 수 없습니다.")
        if current_user.role == UserRole.SYSTEM_ADMIN or current_user.id == target.id:
            return target
        if current_user.role == UserRole.DEPARTMENT_MANAGER and current_user.department_id and current_user.department_id == target.department_id:
            return target
        raise forbidden()

    def create_user(self, payload: UserCreate, actor: User, ip_address: str | None, user_agent: str | None) -> User:
        email = normalize_email(payload.email)
        if self.users.get_by_email(email):
            raise api_error(409, ErrorCode.USER_EMAIL_DUPLICATED, "이미 사용 중인 이메일입니다.")
        if payload.department_id and self.departments.get_by_id(payload.department_id) is None:
            raise api_error(404, ErrorCode.DEPARTMENT_NOT_FOUND, "부서를 찾을 수 없습니다.")
        password = validate_password_policy(payload.password, email)
        user = User(email=email, password_hash=hash_password(password), name=payload.name.strip(), role=payload.role, department_id=payload.department_id)
        self.users.create(user)
        self.audit.record(action=AuditAction.USER_CREATE, actor_id=actor.id, target_type="User", target_id=str(user.id), ip_address=ip_address, user_agent=user_agent, details={"email": email, "role": payload.role.value})
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_user(self, user_id: uuid.UUID, payload: UserUpdate, actor: User, ip_address: str | None, user_agent: str | None) -> User:
        target = self.users.get_by_id(user_id)
        if target is None:
            raise api_error(404, ErrorCode.USER_NOT_FOUND, "사용자를 찾을 수 없습니다.")
        changes: dict[str, object] = {}
        if payload.department_id is not None and self.departments.get_by_id(payload.department_id) is None:
            raise api_error(404, ErrorCode.DEPARTMENT_NOT_FOUND, "부서를 찾을 수 없습니다.")
        if payload.name is not None and payload.name != target.name:
            changes["name"] = {"before": target.name, "after": payload.name}
            target.name = payload.name.strip()
        if payload.department_id is not None and payload.department_id != target.department_id:
            changes["department_id"] = {"before": str(target.department_id), "after": str(payload.department_id)}
            target.department_id = payload.department_id
        if payload.role is not None and payload.role != target.role:
            self._ensure_not_last_admin(target, new_role=payload.role)
            changes["role"] = {"before": target.role.value, "after": payload.role.value}
            target.role = payload.role
            self.audit.record(action=AuditAction.USER_ROLE_CHANGE, actor_id=actor.id, target_type="User", target_id=str(target.id), ip_address=ip_address, user_agent=user_agent, details=changes)
        if payload.is_active is not None and payload.is_active != target.is_active:
            self._ensure_not_last_admin(target, new_is_active=payload.is_active)
            changes["is_active"] = {"before": target.is_active, "after": payload.is_active}
            target.is_active = payload.is_active
            self.audit.record(action=AuditAction.USER_ACTIVATE if payload.is_active else AuditAction.USER_DEACTIVATE, actor_id=actor.id, target_type="User", target_id=str(target.id), ip_address=ip_address, user_agent=user_agent)
        if changes:
            self.audit.record(action=AuditAction.USER_UPDATE, actor_id=actor.id, target_type="User", target_id=str(target.id), ip_address=ip_address, user_agent=user_agent, details=changes)
        self.db.commit()
        self.db.refresh(target)
        return target

    def _ensure_not_last_admin(self, target: User, new_role: UserRole | None = None, new_is_active: bool | None = None) -> None:
        removing_admin = target.role == UserRole.SYSTEM_ADMIN and (new_role is not None and new_role != UserRole.SYSTEM_ADMIN or new_is_active is False)
        if removing_admin and self.users.count_system_admins() <= 1:
            raise api_error(400, ErrorCode.FORBIDDEN, "마지막 SYSTEM_ADMIN은 변경하거나 비활성화할 수 없습니다.")
