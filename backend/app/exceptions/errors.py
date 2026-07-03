from fastapi import HTTPException, status


class ErrorCode:
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_INACTIVE_USER = "AUTH_INACTIVE_USER"
    AUTH_INVALID_TOKEN = "AUTH_INVALID_TOKEN"
    AUTH_EXPIRED_TOKEN = "AUTH_EXPIRED_TOKEN"
    AUTH_REFRESH_TOKEN_REQUIRED = "AUTH_REFRESH_TOKEN_REQUIRED"
    AUTH_REFRESH_TOKEN_REVOKED = "AUTH_REFRESH_TOKEN_REVOKED"
    FORBIDDEN = "FORBIDDEN"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    USER_EMAIL_DUPLICATED = "USER_EMAIL_DUPLICATED"
    DEPARTMENT_NOT_FOUND = "DEPARTMENT_NOT_FOUND"
    DEPARTMENT_NAME_DUPLICATED = "DEPARTMENT_NAME_DUPLICATED"
    INVALID_ROLE = "INVALID_ROLE"
    VALIDATION_ERROR = "VALIDATION_ERROR"


def api_error(status_code: int, code: str, message: str, details: object | None = None) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"error": {"code": code, "message": message, "details": details}})


def forbidden() -> HTTPException:
    return api_error(status.HTTP_403_FORBIDDEN, ErrorCode.FORBIDDEN, "접근 권한이 없습니다.")
