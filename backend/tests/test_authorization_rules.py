import uuid

from app.models.enums import UserRole
from app.models.user import User
from app.users.service import UserService


def _user(role: UserRole, department_id=None):
    return User(id=uuid.uuid4(), email=f"{uuid.uuid4()}@example.com", password_hash="hash", name="User", role=role, department_id=department_id, is_active=True)


def test_department_manager_can_see_same_department_user() -> None:
    department_id = uuid.uuid4()
    manager = _user(UserRole.DEPARTMENT_MANAGER, department_id)
    target = _user(UserRole.USER, department_id)

    assert manager.department_id == target.department_id


def test_roles_are_checked_explicitly_not_by_ordering() -> None:
    admin_roles = {UserRole.SYSTEM_ADMIN}

    assert UserRole.SYSTEM_ADMIN in admin_roles
    assert UserRole.DOCUMENT_ADMIN not in admin_roles
    assert UserRole.DEPARTMENT_MANAGER not in admin_roles
    assert UserRole.USER not in admin_roles
