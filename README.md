# SecureDocs AI Hub

SecureDocs AI Hub는 기업 문서 자산을 중앙에서 관리하고 접근제어, 버전 관리, 협업, 감사 로그, AI 추천, 권한 필터가 적용된 RAG 문서 채팅을 제공하기 위한 포트폴리오용 프로토타입입니다. 특정 상용 제품의 소스코드나 화면을 복제하지 않고 일반적인 기업용 문서중앙화 및 AI 지식관리 요구사항을 직접 설계합니다.

## 이번 기반 작업 범위

- Docker Compose 기반 `nginx`, `frontend`, `backend`, `postgres`, `redis`, `minio`, `minio-init` 구성
- PostgreSQL `pgvector` 확장 초기화
- MinIO 기본 버킷 생성: `documents-original`, `documents-preview`, `documents-backup`, `database-backup`
- FastAPI 기본 애플리케이션과 `/api/v1/health` 상태 확인 API
- PostgreSQL, Redis, MinIO 연결 상태 확인
- Next.js App Router 기반 관리자 레이아웃과 상태 확인 화면
- Nginx 리버스 프록시
- 백엔드 헬스체크 테스트

## 사전 요구사항

- Docker 및 Docker Compose plugin
- Python 3.12 이상
- Node.js 22 이상 및 npm

## 디렉터리 구조

```text
backend/app          FastAPI 애플리케이션
backend/tests        Pytest 테스트
frontend/app         Next.js App Router 화면
frontend/components  공통 레이아웃 컴포넌트
nginx                리버스 프록시 설정
postgres/init        PostgreSQL 초기화 SQL
scripts              반복 검증 스크립트
```

## 환경변수

`.env.example`은 개발용 예시값만 포함합니다. 실제 운영 비밀값은 커밋하지 말고 배포 환경의 Secret 또는 로컬 `.env`로 관리하세요.

```bash
cp .env.example .env
```

`NEXT_PUBLIC_API_BASE_URL`은 브라우저에서 사용할 공개 API 주소이고, `API_INTERNAL_BASE_URL`은 Docker 내부의 Next.js 서버 컴포넌트가 백엔드에 접근할 때 사용하는 서버 전용 주소입니다.

`CORS_ORIGINS`는 쉼표 구분 문자열(`http://localhost,http://localhost:3000`) 또는 JSON 배열 문자열(`["http://localhost","http://localhost:3000"]`)을 지원합니다. `*`는 자동으로 추가하지 않으며 빈 항목은 제거됩니다.

## 최초 실행

```bash
docker compose up --build
```

접속 URL:

- 프론트엔드: <http://localhost>
- FastAPI Swagger UI: <http://localhost/docs>
- OpenAPI JSON: <http://localhost/openapi.json>
- 헬스체크 API: <http://localhost/api/v1/health>
- MinIO 콘솔: <http://localhost:9001>

## 전체 종료

```bash
docker compose down
```

## 볼륨까지 삭제하는 초기화

```bash
docker compose down -v
```

다시 실행하면 PostgreSQL의 `vector` 확장과 MinIO 버킷이 재생성됩니다.

## 서비스별 로그 확인

```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f nginx
docker compose logs -f postgres
docker compose logs -f redis
docker compose logs -f minio
```

## 상태 확인 API

모든 의존 서비스가 연결되면 `/api/v1/health`는 다음과 같이 응답합니다.

```json
{
  "status": "healthy",
  "services": {
    "database": "up",
    "redis": "up",
    "object_storage": "up"
  }
}
```

일부 서비스가 연결되지 않으면 `503 Service Unavailable`과 함께 `status`가 `unhealthy`로 반환됩니다. 응답과 로그에는 비밀번호, 토큰, access key, 전체 연결 문자열을 포함하지 않습니다.

## PostgreSQL 및 pgvector 확인

PostgreSQL은 `pgvector/pgvector:pg16` 이미지를 사용하며 초기화 SQL에서 다음을 실행합니다.

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Docker 실행 후 pgvector 확장은 다음 명령으로 확인합니다.

```bash
docker compose exec postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT extname FROM pg_extension WHERE extname = 'vector';"
```

## MinIO 버킷 확인

`minio-init`는 MinIO 준비 완료 이후 `mc mb --ignore-existing`로 네 개의 필수 버킷을 멱등적으로 생성합니다.

```bash
docker compose run --rm minio-init
```

헬스체크는 단순 서버 연결만이 아니라 애플리케이션 준비 상태를 확인하기 위해 네 개 필수 버킷이 모두 존재하는지 검사합니다. 버킷 누락은 문서 원본, 미리보기, 문서 백업, DB 백업 흐름의 기반 결함이므로 `object_storage: down`으로 표시합니다.

## worker 현재 상태와 역할

Celery 앱과 백그라운드 작업은 아직 구현 범위가 아닙니다. `worker` 서비스는 `worker` profile에 넣어 기본 `docker compose up`에서는 시작하지 않도록 명확히 비활성화했습니다. 실행 가능성 검증을 위해 `python -m app.worker` 진입점은 존재하지만, 현재는 기반 단계 안내 메시지를 출력하고 종료합니다.

```bash
docker compose --profile worker run --rm worker
```

## 로컬 테스트와 정적 검사

백엔드 테스트:

```bash
cd backend
python -m pytest
```

프론트엔드 검사:

```bash
cd frontend
npm ci
npm run type-check
npm run lint
npm run build
```

전체 반복 검증:

```bash
./scripts/verify.sh
```

## Docker를 실행할 수 없을 때 가능한 정적 검사

Docker가 없는 환경에서는 실제 컨테이너 실행 성공을 검증했다고 표현하지 마세요. 대신 다음 범위만 확인할 수 있습니다.

```bash
python - <<'PY'
import ast, pathlib
for root in ('backend/app', 'backend/tests'):
    for path in pathlib.Path(root).rglob('*.py'):
        ast.parse(path.read_text(), filename=str(path))
print('python-ast-ok')
PY
git diff --check
```

## 아직 구현하지 않은 기능

이번 작업은 기반 환경 검증 및 보정 범위입니다. 인증, JWT, 사용자·부서·역할 관리, 문서 업로드, 문서 권한, RAG, AI 추천, 백업 실행 로직, 협업 기능은 후속 작업에서 구현합니다.

## 인증·사용자·부서 관리

이번 단계의 백엔드는 이메일/비밀번호 로그인, JWT Access Token, HttpOnly Refresh Token 쿠키, 사용자/부서 관리 API, 감사 로그를 제공합니다. Access Token은 `Authorization: Bearer <token>` 헤더로 전달하고 Refresh Token 원문은 JSON 응답에 포함하지 않으며 `securedocs_refresh_token` HttpOnly 쿠키에 저장합니다.

### 역할별 권한

- `SYSTEM_ADMIN`: 사용자/부서 생성과 수정, 사용자 활성화/비활성화, 역할 변경, 관리자 API 접근
- `DOCUMENT_ADMIN`: 이번 단계에서는 자신의 정보 조회만 허용
- `DEPARTMENT_MANAGER`: 동일 부서 사용자 조회와 자신의 정보 조회
- `USER`: 자신의 정보 조회

역할은 문자열 순서가 아니라 필요한 역할을 명시적으로 검사합니다.

### Alembic 마이그레이션

```bash
cd backend
alembic upgrade head
```

Docker 환경에서는 다음과 같이 실행합니다.

```bash
docker compose exec backend alembic upgrade head
```

### 초기 SYSTEM_ADMIN 생성

애플리케이션 시작 시 기본 관리자를 자동 생성하지 않습니다. 마이그레이션 후 명시적으로 다음 명령을 실행하세요.

```bash
cd backend
INITIAL_ADMIN_EMAIL=admin@example.com INITIAL_ADMIN_PASSWORD='ExamplePassword1!' INITIAL_ADMIN_NAME='관리자' python -m app.scripts.create_admin
```

Docker 환경:

```bash
docker compose exec backend python -m app.scripts.create_admin
```

동일 이메일 사용자가 이미 있으면 중복 생성하지 않고 메시지만 출력합니다. 비밀번호는 로그에 출력하지 않습니다.

### 로그인 API 예시

```bash
curl -i -X POST http://localhost/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"ExamplePassword1!"}'
```

응답 JSON에는 Access Token만 포함되며 Refresh Token은 HttpOnly 쿠키로 설정됩니다. 개발 환경에서는 `.env`의 `REFRESH_COOKIE_SECURE=false`, `REFRESH_COOKIE_SAMESITE=lax`를 사용하고 운영 환경에서는 HTTPS 전제로 Secure 쿠키를 사용하세요.

### 구현된 인증 API

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/users`
- `POST /api/v1/users`
- `GET /api/v1/users/{user_id}`
- `PATCH /api/v1/users/{user_id}`
- `GET /api/v1/departments`
- `POST /api/v1/departments`
- `GET /api/v1/departments/{department_id}`
- `PATCH /api/v1/departments/{department_id}`

### 아직 구현하지 않은 인증 관련 항목

프론트엔드 사용자/부서 화면은 기반 UI만 제공하며 실제 폼 상태와 API 연동은 후속 작업에서 보강합니다. 문서 업로드, 문서 ACL, RAG, AI 추천, 백업 실행 로직은 아직 구현하지 않았습니다.

## 문서 메타데이터·업로드 기반

이번 단계는 문서 ACL, 본문 추출, OCR, 임베딩, RAG 없이 최초 문서 업로드와 원본 파일 저장 기반만 제공합니다.

### 업로드 흐름

인증된 활성 사용자가 `POST /api/v1/documents`에 `multipart/form-data`로 `title`, `description`, `file`을 전달하면 백엔드는 제목, 크기, 확장자, MIME 타입, 파일 서명을 검증하고 SHA-256 체크섬을 계산합니다. 이후 `Document`와 최초 `DocumentVersion(version_number=1)`을 만들고 MinIO `documents-original` 버킷에 업로드한 뒤 `current_version_id`를 연결하고 상태를 `ACTIVE`로 전환합니다.

### 지원 파일 형식과 크기

기본 허용 확장자는 `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.txt`, `.md`이며 `.env`의 `DOCUMENT_ALLOWED_EXTENSIONS`로 관리합니다. 기본 최대 크기는 `DOCUMENT_MAX_UPLOAD_SIZE_MB=50`입니다. 브라우저 검증은 편의 기능이며 백엔드 검증이 최종 기준입니다.

### MinIO 저장 키 정책

원본 파일은 `documents-original` 버킷에 저장합니다. 저장 키는 `documents/{owner_id}/{document_id}/{version_id}/{uuid}.{extension}` 형식이며 사용자가 제공한 파일명은 경로에 사용하지 않습니다. 원본 파일명과 정규화 파일명은 메타데이터로만 저장합니다.

### 체크섬과 MIME 검증

업로드 바이트에서 SHA-256 체크섬을 계산해 `document_versions.checksum_sha256`에 저장합니다. 확장자와 Content-Type을 함께 확인하고 PDF/Office Open XML 파일은 기본 파일 서명도 확인합니다. ClamAV 연동 위치는 `documents.validators` 이후 업로드 전 단계이며, 현재 실제 ClamAV 검사는 수행하지 않습니다.

### 임시 접근제어 정책

문서 ACL이 아직 없으므로 임시 역할 정책을 사용합니다. `SYSTEM_ADMIN`은 모든 문서 메타데이터와 다운로드/삭제가 가능하고, `DOCUMENT_ADMIN`은 모든 메타데이터를 볼 수 있지만 자신이 업로드한 문서만 다운로드/삭제할 수 있습니다. `DEPARTMENT_MANAGER`는 같은 부서 문서 메타데이터를 볼 수 있으나 다른 사용자의 원본 다운로드는 금지됩니다. `USER`는 자신이 업로드한 문서만 접근할 수 있습니다. 이 정책은 향후 문서 ACL로 교체됩니다.

### 논리 삭제와 일관성 처리

삭제 API는 DB 레코드와 MinIO 객체를 즉시 제거하지 않고 `is_deleted=true`, `deleted_at`만 갱신합니다. 업로드 중 MinIO 저장 후 DB 처리 실패가 발생하면 업로드한 객체 삭제를 보상 처리로 시도합니다. 삭제 실패 가능성이 있으므로 향후 고아 객체 정리 작업이 필요합니다.

### 문서 API 예시

```bash
curl -i -X POST http://localhost/api/v1/documents \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "title=보안 정책" \
  -F "description=초기 문서" \
  -F "file=@policy.pdf;type=application/pdf"
```

다운로드는 `GET /api/v1/documents/{document_id}/download`에서 presigned URL을 반환하지 않고 백엔드 `StreamingResponse`로 원본 파일을 전달합니다. 목록 조회 감사 로그는 과도한 로그 생성을 피하기 위해 현재 기록하지 않고, 업로드·상세조회·다운로드·삭제만 기록합니다.

### 아직 구현하지 않은 문서 기능

문서별 ACL, 사용자/부서 공유, 외부 공유 링크, 두 번째 버전 업로드, 본문 추출, OCR, 임베딩, RAG, AI 분류/추천, ClamAV 실제 검사, PDF 미리보기, 영구 삭제와 보존 정책은 후속 단계에서 구현합니다.

## 프론트엔드 인증 세션

프론트엔드는 로그인 성공 응답의 `access_token`과 사용자 요약 정보를 Zustand 기반 메모리 상태로만 보관합니다. Access Token, Refresh Token, 비밀번호, 전체 로그인 응답은 `localStorage` 또는 `sessionStorage`에 저장하지 않습니다.

### 인증 상태 구조

인증 상태는 `loading`, `authenticated`, `unauthenticated` 세 단계로 관리합니다. 앱 시작 시 `loading`으로 시작하고, HttpOnly Refresh Token 쿠키를 이용해 `/api/v1/auth/refresh`를 호출한 뒤 성공하면 Access Token과 사용자 정보를 메모리에 복구합니다. 실패하면 세션을 비우고 `unauthenticated`로 전환합니다.

### Refresh Token 쿠키와 복구

Refresh Token은 백엔드가 설정하는 HttpOnly 쿠키로 유지되며 브라우저 JavaScript에서 직접 읽지 않습니다. 새로고침으로 메모리 Access Token이 사라져도 앱 시작 시 refresh 요청을 통해 세션을 복구합니다.

### 공통 API client와 401 재시도

브라우저 보호 API 요청은 공통 API client를 사용합니다. client는 메모리 Access Token이 있으면 `Authorization: Bearer <access_token>` 헤더를 자동으로 추가하고 모든 요청에 `credentials: include`를 적용합니다. JSON 요청에는 `Content-Type: application/json`을 설정하지만, `FormData` 요청에는 브라우저가 multipart boundary를 지정하도록 `Content-Type`을 직접 설정하지 않습니다.

보호 API가 `401 Unauthorized`를 반환하면 refresh 요청을 한 번만 실행하고, 성공 시 원래 요청을 한 번 재시도합니다. Refresh Token 회전 정책 때문에 여러 요청이 동시에 401을 받더라도 공유 refresh Promise를 사용해 refresh 요청은 하나만 실행합니다. refresh 실패 시 프론트엔드 세션을 제거하고 로그인 화면으로 이동합니다.

### 보호 페이지와 역할별 메뉴

`/dashboard`, `/documents`, `/admin/users`, `/admin/departments`는 공통 보호 컴포넌트를 통해 인증 상태를 확인합니다. 인증 확인 중에는 로딩 UI를 보여 주고, 미인증 사용자는 `/login?next=<원래경로>`로 이동합니다. 관리자 화면은 `SYSTEM_ADMIN` 사용자에게만 표시하며, 사이드바에서도 사용자/부서 관리 메뉴는 `SYSTEM_ADMIN`에게만 노출합니다. 이 프론트엔드 역할 검사는 편의 UI이며 실제 권한 검사는 백엔드 API에서 다시 수행합니다.

### 로그아웃

로그아웃 버튼은 `/api/v1/auth/logout`을 호출해 백엔드 Refresh Token 폐기를 요청한 뒤, 요청 성공 여부와 관계없이 프론트엔드 메모리 세션을 제거하고 `/login`으로 이동합니다.

### 프론트엔드 인증 테스트

의존성이 설치된 환경에서 다음 명령으로 타입 검사, 린트, 빌드와 인증 client 정적 검사를 실행합니다.

```bash
cd frontend
npm ci
npm run type-check
npm run lint
npm run build
npm run test:auth
```

## 문서 다운로드 스트리밍

문서 다운로드는 MinIO presigned URL을 브라우저에 반환하지 않고 백엔드가 MinIO 객체를 열어 `StreamingResponse`로 전달합니다. 이 구조는 Docker 내부 호스트명인 `minio:9000`을 브라우저에 노출하지 않고, 다운로드 직전까지 Access Token 인증과 역할·소유권 기반 권한 검사를 백엔드에서 유지하기 위한 선택입니다.

다운로드 응답에는 저장된 MIME 타입, `Content-Length`, `Cache-Control: private, no-store`, `X-Content-Type-Options: nosniff`, 그리고 RFC 5987 형식의 `Content-Disposition`을 설정합니다. 파일명은 원본 파일명 또는 정규화 파일명을 기반으로 하되 CR/LF, NUL, 따옴표, 경로 구분자 등 헤더 인젝션과 경로 조작에 사용할 수 있는 문자를 제거합니다. `storage_key`, MinIO endpoint, access key, secret key는 응답과 감사 로그에 포함하지 않습니다.

현재 MVP는 동기 MinIO SDK 응답을 청크 단위로 `StreamingResponse`에 연결합니다. 스트림 반복이 끝나거나 예외가 발생하면 MinIO 응답 객체의 `close()`와 `release_conn()`을 호출해 네트워크 자원을 해제합니다. 대용량 파일과 많은 동시 다운로드에서는 워커 수, 전용 파일 전송 계층, 비동기 object storage client 또는 내부 가속 프록시를 검토해야 합니다.

다운로드 감사 로그는 성공 시 `DOCUMENT_DOWNLOAD`에 `result=success`를 기록하고, 실패 시 같은 action에 `result=failed`와 안전한 오류 코드만 기록합니다. 감사 로그에는 문서 본문, 파일 바이너리, `storage_key`, presigned URL, MinIO credential, Access Token, Refresh Token을 저장하지 않습니다. 감사 로그 저장 실패가 스트림 중간 손상을 만들지 않도록 현재는 스트림을 열기 전 메타데이터와 감사 로그를 처리합니다.

프론트엔드는 다운로드 API를 JSON URL 응답으로 처리하지 않고 인증 API client의 Blob 다운로드 함수를 사용합니다. 응답의 `Content-Disposition`에서 `filename*`, `filename` 순서로 파일명을 추출하고, 없으면 현재 문서 파일명 또는 안전한 기본 이름을 사용합니다. 생성한 object URL은 클릭 후 즉시 `URL.revokeObjectURL()`로 해제합니다.

### npm 재현성

프론트엔드는 npm을 단일 패키지 매니저로 사용합니다. 의존성 설치가 가능한 환경에서는 다음 명령으로 `package-lock.json`을 생성 또는 갱신하고 커밋해야 합니다.

```bash
cd frontend
npm install
npm ci
```

현재 저장소는 `node_modules`를 커밋하지 않습니다. lock 파일이 생성된 뒤에는 Dockerfile의 dependency 설치도 재현 가능한 `npm ci` 기반으로 전환해야 합니다. 현재 실행 환경에서는 registry 403으로 lock 파일 생성을 완료하지 못했으므로 Dockerfile의 기존 `npm install` 동작은 유지했습니다.

### 업로드·다운로드 무결성 확인

TXT 또는 PDF를 업로드한 뒤 다운로드 파일과 원본 파일의 SHA-256을 비교합니다.

```bash
sha256sum sample.txt
sha256sum downloaded-sample.txt
```

두 값이 같으면 MinIO 저장과 백엔드 스트리밍 다운로드 과정에서 파일 내용이 보존된 것입니다.
