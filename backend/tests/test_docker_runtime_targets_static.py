from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text()


def test_backend_dockerfile_has_safe_runtime_final_stage_and_test_stage() -> None:
    dockerfile = read("backend/Dockerfile")
    assert "FROM base AS test" in dockerfile
    assert "FROM base AS runtime" in dockerfile
    assert dockerfile.rfind("FROM base AS runtime") > dockerfile.rfind("FROM base AS test")
    assert 'ENV PYTEST_ADDOPTS="--cache-dir=/tmp/securedocs-pytest-cache"' in dockerfile
    assert 'CMD ["python", "-m", "pytest", "-v"]' in dockerfile
    assert 'CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]' in dockerfile


def test_compose_targets_keep_runtime_and_tests_separate() -> None:
    compose = read("docker-compose.yml")
    assert "backend:\n    build:\n      context: ./backend\n      target: runtime" in compose
    assert "backend-test:\n    profiles: [\"test\"]\n    build:\n      context: ./backend\n      target: test" in compose
    assert "worker:\n    profiles: [\"worker\"]\n    build:\n      context: ./backend\n      target: runtime" in compose
    backend_section = compose.split("  backend:", 1)[1].split("  backend-test:", 1)[0]
    assert "pytest" not in backend_section


def test_verify_script_checks_backend_command_and_test_profile() -> None:
    verify = read("scripts/verify.sh")
    assert "docker compose config --format json" in verify
    assert 'services["backend"]["build"]["target"] == "runtime"' in verify
    assert 'services["backend-test"]["build"]["target"] == "test"' in verify
    assert 'services["worker"]["build"]["target"] == "runtime"' in verify
    assert "docker inspect \"$backend_id\"" in verify
    assert '"$backend_cmd" != *"uvicorn"*' in verify
    assert '"$backend_cmd" == *"pytest"*' in verify
    assert "docker compose --profile test run --rm backend-test python -m pytest -v" in verify
