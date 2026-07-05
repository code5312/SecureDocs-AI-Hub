from enum import StrEnum


class ExtractionErrorCode(StrEnum):
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    OBJECT_NOT_FOUND = "OBJECT_NOT_FOUND"
    OBJECT_TOO_LARGE = "OBJECT_TOO_LARGE"
    ENCRYPTED_DOCUMENT = "ENCRYPTED_DOCUMENT"
    PAGE_LIMIT_EXCEEDED = "PAGE_LIMIT_EXCEEDED"
    SLIDE_LIMIT_EXCEEDED = "SLIDE_LIMIT_EXCEEDED"
    SHEET_LIMIT_EXCEEDED = "SHEET_LIMIT_EXCEEDED"
    CHARACTER_LIMIT_EXCEEDED = "CHARACTER_LIMIT_EXCEEDED"
    CHUNK_LIMIT_EXCEEDED = "CHUNK_LIMIT_EXCEEDED"
    PARSER_ERROR = "PARSER_ERROR"
    STORAGE_UNAVAILABLE = "STORAGE_UNAVAILABLE"
    QUEUE_UNAVAILABLE = "QUEUE_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


_SAFE_MESSAGES = {
    ExtractionErrorCode.UNSUPPORTED_FORMAT: "지원하지 않는 문서 형식입니다.",
    ExtractionErrorCode.OBJECT_NOT_FOUND: "문서 원본 파일을 찾을 수 없습니다.",
    ExtractionErrorCode.OBJECT_TOO_LARGE: "문서 파일이 추출 제한보다 큽니다.",
    ExtractionErrorCode.ENCRYPTED_DOCUMENT: "암호화된 문서는 텍스트 추출을 지원하지 않습니다.",
    ExtractionErrorCode.PAGE_LIMIT_EXCEEDED: "문서 페이지 수가 추출 제한을 초과했습니다.",
    ExtractionErrorCode.SLIDE_LIMIT_EXCEEDED: "슬라이드 수가 추출 제한을 초과했습니다.",
    ExtractionErrorCode.SHEET_LIMIT_EXCEEDED: "시트 수가 추출 제한을 초과했습니다.",
    ExtractionErrorCode.CHARACTER_LIMIT_EXCEEDED: "추출된 텍스트가 허용 문자 수를 초과했습니다.",
    ExtractionErrorCode.CHUNK_LIMIT_EXCEEDED: "생성된 청크 수가 허용 개수를 초과했습니다.",
    ExtractionErrorCode.PARSER_ERROR: "문서 텍스트를 추출할 수 없습니다.",
    ExtractionErrorCode.STORAGE_UNAVAILABLE: "문서 저장소를 사용할 수 없습니다.",
    ExtractionErrorCode.QUEUE_UNAVAILABLE: "추출 작업을 대기열에 등록할 수 없습니다.",
    ExtractionErrorCode.INTERNAL_ERROR: "문서 추출 중 오류가 발생했습니다.",
}


class ExtractionError(Exception):
    def __init__(self, code: ExtractionErrorCode, message: str | None = None) -> None:
        self.code = code
        self.safe_message = message or _SAFE_MESSAGES[code]
        super().__init__(self.safe_message)
