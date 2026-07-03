from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.auth.schemas import LoginRequest, TokenResponse
from app.auth.service import AuthService
from app.config.settings import get_settings
from app.database.session import get_db
from app.dependencies.auth import get_current_user, request_ip
from app.models.user import User
from app.users.schemas import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_refresh_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=token,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/api/v1/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(key=settings.refresh_cookie_name, path="/api/v1/auth")


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    access_token, expires_in, refresh_token, user = AuthService(db).login(email=payload.email, password=payload.password, ip_address=request_ip(request), user_agent=request.headers.get("user-agent"))
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(access_token=access_token, expires_in=expires_in, user=UserRead.model_validate(user))


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    settings = get_settings()
    access_token, expires_in, refresh_token, user = AuthService(db).refresh(raw_refresh_token=request.cookies.get(settings.refresh_cookie_name), ip_address=request_ip(request), user_agent=request.headers.get("user-agent"))
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(access_token=access_token, expires_in=expires_in, user=UserRead.model_validate(user))


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> dict[str, str]:
    settings = get_settings()
    AuthService(db).logout(raw_refresh_token=request.cookies.get(settings.refresh_cookie_name), ip_address=request_ip(request), user_agent=request.headers.get("user-agent"))
    _clear_refresh_cookie(response)
    return {"status": "ok"}


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)
