import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_current_user, request_ip, require_system_admin
from app.models.enums import UserRole
from app.models.user import User
from app.users.schemas import UserCreate, UserRead, UserUpdate
from app.users.service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db), offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), email: str | None = None, name: str | None = None, role: UserRole | None = None, department_id: uuid.UUID | None = None, is_active: bool | None = None) -> list[UserRead]:
    users = UserService(db).list_users(current_user, offset=offset, limit=limit, email=email, name=name, role=role, department_id=department_id, is_active=is_active)
    return [UserRead.model_validate(user) for user in users]


@router.post("", response_model=UserRead, status_code=201)
def create_user(payload: UserCreate, request: Request, current_user: User = Depends(require_system_admin), db: Session = Depends(get_db)) -> UserRead:
    user = UserService(db).create_user(payload, actor=current_user, ip_address=request_ip(request), user_agent=request.headers.get("user-agent"))
    return UserRead.model_validate(user)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserRead:
    return UserRead.model_validate(UserService(db).get_visible_user(current_user, user_id))


@router.patch("/{user_id}", response_model=UserRead)
def update_user(user_id: uuid.UUID, payload: UserUpdate, request: Request, current_user: User = Depends(require_system_admin), db: Session = Depends(get_db)) -> UserRead:
    user = UserService(db).update_user(user_id, payload, actor=current_user, ip_address=request_ip(request), user_agent=request.headers.get("user-agent"))
    return UserRead.model_validate(user)
