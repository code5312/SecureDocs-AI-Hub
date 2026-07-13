from pathlib import Path

from tests.repository_paths import find_repository_root

ROOT = find_repository_root(Path(__file__))


def read(path: str) -> str:
    return (ROOT / path).read_text()


def test_backend_dockerfile_has_safe_runtime_final_stage_and_test_stage() -> None:
    dockerfile = read("backend/Dockerfile")
    assert "FROM base AS test" in dockerfile
    assert "FROM base AS runtime" in dockerfile
    assert dockerfile.rfind("FROM base AS runtime") > dockerfile.rfind("FROM base AS test")
    assert "PYTEST_ADDOPTS" not in dockerfile
    assert "--cache-dir" not in dockerfile
    assert "WORKDIR /workspace/backend" in dockerfile
    assert "COPY backend/requirements.txt ./requirements.txt" in dockerfile
    assert "COPY --chown=app:app backend/app ./app" in dockerfile
    assert "COPY --chown=app:app backend/alembic ./alembic" in dockerfile
    assert "COPY --chown=app:app backend/tests ./tests" in dockerfile
    assert "COPY --chown=app:app backend/pytest.ini ./pytest.ini" in dockerfile
    assert "COPY --chown=app:app backend/Dockerfile ./Dockerfile" in dockerfile
    assert "COPY --chown=app:app docker-compose.yml /workspace/docker-compose.yml" in dockerfile
    assert "COPY --chown=app:app scripts /workspace/scripts" in dockerfile
    assert "COPY --chown=app:app nginx /workspace/nginx" in dockerfile
    pytest_ini = read("backend/pytest.ini")
    assert "cache_dir = /tmp/securedocs-pytest-cache" in pytest_ini
    assert 'CMD ["python", "-m", "pytest", "-v"]' in dockerfile
    assert 'CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]' in dockerfile


def test_compose_targets_keep_runtime_and_tests_separate() -> None:
    compose = read("docker-compose.yml")
    assert "backend:\n    build:\n      context: .\n      dockerfile: backend/Dockerfile\n      target: runtime" in compose
    assert "backend-test:\n    profiles: [\"test\"]\n    build:\n      context: .\n      dockerfile: backend/Dockerfile\n      target: test" in compose
    assert "worker:\n    profiles: [\"worker\"]\n    build:\n      context: .\n      dockerfile: backend/Dockerfile\n      target: runtime" in compose
    backend_section = compose.split("  backend:", 1)[1].split("  backend-test:", 1)[0]
    assert "pytest" not in backend_section
    backend_test_section = compose.split("  backend-test:", 1)[1].split("  worker:", 1)[0]
    assert "source: ./.dockerignore" in backend_test_section
    assert "target: /workspace/.dockerignore" in backend_test_section
    assert "read_only: true" in backend_test_section


def test_verify_script_checks_backend_command_and_test_profile() -> None:
    verify = read("scripts/verify.sh")
    assert "docker compose --profile test --profile worker config --format json" in verify
    assert 'services["backend"]["build"]["target"] == "runtime"' in verify
    assert 'services["backend-test"]["build"]["target"] == "test"' in verify
    assert 'services["worker"]["build"]["target"] == "runtime"' in verify
    assert "docker inspect \"$backend_id\"" in verify
    assert '"$backend_cmd" != *"uvicorn"*' in verify
    assert '"$backend_cmd" == *"pytest"*' in verify
    assert "docker compose run --rm --no-deps backend python -c" in verify
    assert "docker compose up -d postgres redis minio" in verify
    assert "docker compose run --rm backend alembic upgrade head" in verify
    assert "docker compose up -d backend" in verify
    assert "docker compose up -d frontend" in verify
    assert "docker compose up -d nginx" in verify
    assert "docker compose exec -T nginx nginx -t" in verify
    assert "docker compose --profile test run --rm backend-test python -m pytest -v" in verify


def test_phase_a_verify_uses_container_test_paths_and_smoke_skip_message() -> None:
    verify_phase_a = read("scripts/verify_phase_a.sh")
    assert "TARGETED_TESTS=(" in verify_phase_a
    assert "tests/test_extraction_static.py" in verify_phase_a
    assert "backend/tests/test_extraction_static.py" not in verify_phase_a
    assert "docker compose --profile test run --rm backend-test python -m pytest -q" in verify_phase_a
    assert "SKIP: extraction API smoke test requires SECUREDOCS_ADMIN_EMAIL and SECUREDOCS_ADMIN_PASSWORD" in verify_phase_a


def test_root_dockerignore_keeps_backend_context_small_without_hiding_sources() -> None:
    dockerignore = read(".dockerignore")
    assert "frontend/node_modules" in dockerignore
    assert "frontend/.next" in dockerignore
    assert ".env.*" in dockerignore
    assert "!.env.example" in dockerignore
    assert "backend/Dockerfile" not in dockerignore
    assert "docker-compose.yml" not in dockerignore
