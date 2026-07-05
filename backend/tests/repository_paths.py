import os
from pathlib import Path


def find_repository_root(start: Path | None = None) -> Path:
    configured = os.getenv("SECUREDOCS_REPOSITORY_ROOT")
    if configured:
        candidate = Path(configured).resolve()
        if _is_repository_root(candidate):
            return candidate
        raise RuntimeError(f"SECUREDOCS_REPOSITORY_ROOT does not point to a repository root: {candidate}")

    current = (start or Path(__file__)).resolve()
    for candidate in (current, *current.parents):
        if _is_repository_root(candidate):
            return candidate

    raise RuntimeError(f"Could not locate repository root from {current}")


def _is_repository_root(candidate: Path) -> bool:
    return (
        (candidate / "docker-compose.yml").is_file()
        and (candidate / "backend").is_dir()
        and (candidate / "nginx").is_dir()
    )
