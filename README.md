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
