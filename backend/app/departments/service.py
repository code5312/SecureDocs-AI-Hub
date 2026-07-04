import uuid

from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.departments.repository import DepartmentRepository
from app.departments.schemas import DepartmentCreate, DepartmentUpdate
from app.exceptions import ErrorCode, api_error
from app.models.department import Department
from app.models.enums import AuditAction
from app.models.user import User


class DepartmentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.departments = DepartmentRepository(db)
        self.audit = AuditService(db)

    def list_departments(self, active_only: bool) -> list[Department]:
        return self.departments.list(active_only=active_only)

    def get_department(self, department_id: uuid.UUID) -> Department:
        department = self.departments.get_by_id(department_id)
        if department is None:
            raise api_error(404, ErrorCode.DEPARTMENT_NOT_FOUND, "부서를 찾을 수 없습니다.")
        return department

    def create_department(self, payload: DepartmentCreate, actor: User, ip_address: str | None, user_agent: str | None) -> Department:
        name = payload.name.strip()
        if self.departments.get_by_name(name):
            raise api_error(409, ErrorCode.DEPARTMENT_NAME_DUPLICATED, "이미 존재하는 부서명입니다.")
        if payload.parent_id and self.departments.get_by_id(payload.parent_id) is None:
            raise api_error(404, ErrorCode.DEPARTMENT_NOT_FOUND, "상위 부서를 찾을 수 없습니다.")
        department = Department(name=name, description=payload.description, parent_id=payload.parent_id)
        self.departments.create(department)
        self.audit.record(action=AuditAction.DEPARTMENT_CREATE, actor_id=actor.id, target_type="Department", target_id=str(department.id), ip_address=ip_address, user_agent=user_agent, details={"name": name})
        self.db.commit()
        self.db.refresh(department)
        return department

    def update_department(self, department_id: uuid.UUID, payload: DepartmentUpdate, actor: User, ip_address: str | None, user_agent: str | None) -> Department:
        department = self.get_department(department_id)
        changes: dict[str, object] = {}
        if payload.parent_id == department.id:
            raise api_error(422, ErrorCode.VALIDATION_ERROR, "자기 자신을 상위 부서로 지정할 수 없습니다.")
        if payload.parent_id is not None and self.departments.get_by_id(payload.parent_id) is None:
            raise api_error(404, ErrorCode.DEPARTMENT_NOT_FOUND, "상위 부서를 찾을 수 없습니다.")
        if payload.name is not None:
            name = payload.name.strip()
            existing = self.departments.get_by_name(name)
            if existing and existing.id != department.id:
                raise api_error(409, ErrorCode.DEPARTMENT_NAME_DUPLICATED, "이미 존재하는 부서명입니다.")
            changes["name"] = {"before": department.name, "after": name}
            department.name = name
        for field in ("description", "parent_id", "is_active"):
            value = getattr(payload, field)
            if value is not None and value != getattr(department, field):
                changes[field] = {"before": str(getattr(department, field)), "after": str(value)}
                setattr(department, field, value)
        if changes:
            self.audit.record(action=AuditAction.DEPARTMENT_UPDATE, actor_id=actor.id, target_type="Department", target_id=str(department.id), ip_address=ip_address, user_agent=user_agent, details=changes)
        self.db.commit()
        self.db.refresh(department)
        return department
