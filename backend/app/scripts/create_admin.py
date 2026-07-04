import os

from app.auth.security import hash_password, normalize_email, validate_password_policy
from app.database.session import SessionLocal
from app.models.enums import UserRole
from app.models.user import User
from app.users.repository import UserRepository


def main() -> None:
    email = normalize_email(os.environ.get("INITIAL_ADMIN_EMAIL", input("Admin email: ")))
    password = os.environ.get("INITIAL_ADMIN_PASSWORD") or input("Admin password: ")
    name = os.environ.get("INITIAL_ADMIN_NAME", "관리자")
    with SessionLocal() as db:
        users = UserRepository(db)
        if users.get_by_email(email):
            print(f"SYSTEM_ADMIN already exists for {email}")
            return
        password = validate_password_policy(password, email)
        users.create(User(email=email, password_hash=hash_password(password), name=name, role=UserRole.SYSTEM_ADMIN, is_active=True))
        db.commit()
        print(f"SYSTEM_ADMIN created for {email}")


if __name__ == "__main__":
    main()
