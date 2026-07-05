from collections.abc import Callable

import redis

from app.config.settings import get_settings
from app.database.session import check_database
from app.storage.minio_client import check_object_storage

HealthCheck = Callable[[], bool]


def check_redis() -> bool:
    """Return True when Redis responds to PING within a bounded timeout."""
    settings = get_settings()
    client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
    try:
        return bool(client.ping())
    finally:
        client.close()


def collect_health(checks: dict[str, HealthCheck] | None = None) -> dict[str, str]:
    """Collect dependency health without returning sensitive connection details."""
    active_checks = checks or {
        "database": check_database,
        "redis": check_redis,
        "object_storage": check_object_storage,
    }
    services: dict[str, str] = {}
    for name, check in active_checks.items():
        try:
            services[name] = "up" if check() else "down"
        except Exception:
            services[name] = "down"
    return services
