import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import UserRole
from app.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email.lower().strip()))

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user

    def list(self, *, offset: int, limit: int, email: str | None = None, name: str | None = None, role: UserRole | None = None, department_id: uuid.UUID | None = None, is_active: bool | None = None) -> list[User]:
        stmt = select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
        if email:
            stmt = stmt.where(User.email.ilike(f"%{email.lower().strip()}%"))
        if name:
            stmt = stmt.where(User.name.ilike(f"%{name.strip()}%"))
        if role:
            stmt = stmt.where(User.role == role)
        if department_id:
            stmt = stmt.where(User.department_id == department_id)
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        return list(self.db.scalars(stmt))

    def count_system_admins(self) -> int:
        return int(self.db.scalar(select(func.count()).select_from(User).where(User.role == UserRole.SYSTEM_ADMIN, User.is_active.is_(True))) or 0)
