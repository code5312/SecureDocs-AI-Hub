import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.auth import get_current_user, request_ip, require_system_admin
from app.departments.schemas import DepartmentCreate, DepartmentRead, DepartmentUpdate
from app.departments.service import DepartmentService
from app.models.user import User

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("", response_model=list[DepartmentRead])
def list_departments(active_only: bool = True, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[DepartmentRead]:
    return [DepartmentRead.model_validate(department) for department in DepartmentService(db).list_departments(active_only)]


@router.post("", response_model=DepartmentRead, status_code=201)
def create_department(payload: DepartmentCreate, request: Request, current_user: User = Depends(require_system_admin), db: Session = Depends(get_db)) -> DepartmentRead:
    department = DepartmentService(db).create_department(payload, actor=current_user, ip_address=request_ip(request), user_agent=request.headers.get("user-agent"))
    return DepartmentRead.model_validate(department)


@router.get("/{department_id}", response_model=DepartmentRead)
def get_department(department_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> DepartmentRead:
    return DepartmentRead.model_validate(DepartmentService(db).get_department(department_id))


@router.patch("/{department_id}", response_model=DepartmentRead)
def update_department(department_id: uuid.UUID, payload: DepartmentUpdate, request: Request, current_user: User = Depends(require_system_admin), db: Session = Depends(get_db)) -> DepartmentRead:
    department = DepartmentService(db).update_department(department_id, payload, actor=current_user, ip_address=request_ip(request), user_agent=request.headers.get("user-agent"))
    return DepartmentRead.model_validate(department)
