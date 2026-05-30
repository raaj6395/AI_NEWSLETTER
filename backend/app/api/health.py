"""Health check endpoints.

`/health` is a lightweight liveness probe.
`/health/ready` is a readiness probe that verifies PostgreSQL and Redis
connectivity, which is what we use to validate Milestone 1.
"""

import psycopg
import redis
from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Liveness probe — confirms the API process is up."""
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
    }


@router.get("/health/ready")
def readiness() -> dict:
    """Readiness probe — confirms Postgres and Redis are reachable."""
    settings = get_settings()

    checks = {
        "postgres": _check_postgres(settings.database_url),
        "redis": _check_redis(settings.redis_url),
    }
    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}


def _check_postgres(database_url: str) -> str:
    try:
        with psycopg.connect(database_url, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
        return "ok"
    except Exception as exc:  # noqa: BLE001 - report any connectivity failure
        return f"error: {exc}"


def _check_redis(redis_url: str) -> str:
    try:
        client = redis.Redis.from_url(redis_url, socket_connect_timeout=3)
        client.ping()
        return "ok"
    except Exception as exc:  # noqa: BLE001 - report any connectivity failure
        return f"error: {exc}"
