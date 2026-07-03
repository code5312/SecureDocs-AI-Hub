from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.exceptions.errors import ErrorCode


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return a project-wide validation error envelope without leaking internals."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": {"code": ErrorCode.VALIDATION_ERROR, "message": "요청 값을 확인하세요.", "details": exc.errors()}},
    )
