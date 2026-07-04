import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.department import Department


class DepartmentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, department_id: uuid.UUID) -> Department | None:
        return self.db.get(Department, department_id)

    def get_by_name(self, name: str) -> Department | None:
        return self.db.scalar(select(Department).where(Department.name == name.strip()))

    def create(self, department: Department) -> Department:
        self.db.add(department)
        self.db.flush()
        return department

    def list(self, active_only: bool = False) -> list[Department]:
        stmt = select(Department).order_by(Department.name)
        if active_only:
            stmt = stmt.where(Department.is_active.is_(True))
        return list(self.db.scalars(stmt))
