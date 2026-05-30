import time
import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.database import engine
from app.cache import get_redis

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health", summary="Health check — DB + Redis + uptime")
async def health_check():
    """
    Returns the health status of all critical dependencies.
    Used by Docker HEALTHCHECK, NGINX upstream checks, and monitoring.
    Returns HTTP 200 (healthy) or 503 (degraded).
    """
    start = time.time()
    db_status = "ok"
    redis_status = "ok"
    db_latency_ms = None
    redis_latency_ms = None

    # ── PostgreSQL ──────────────────────────────────────────────────────
    try:
        t0 = time.time()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_latency_ms = round((time.time() - t0) * 1000, 2)
    except Exception as exc:
        logger.error("health | DB check failed: %s", exc)
        db_status = "error"

    # ── Redis ───────────────────────────────────────────────────────────
    try:
        t0 = time.time()
        r = await get_redis()
        await r.ping()
        redis_latency_ms = round((time.time() - t0) * 1000, 2)
    except Exception as exc:
        logger.error("health | Redis check failed: %s", exc)
        redis_status = "error"

    overall = "healthy" if db_status == "ok" and redis_status == "ok" else "degraded"
    http_code = 200 if overall == "healthy" else 503

    payload = {
        "status": overall,
        "version": "1.0.0",
        "uptime_check": True,
        "dependencies": {
            "database": {"status": db_status, "latency_ms": db_latency_ms},
            "redis":    {"status": redis_status, "latency_ms": redis_latency_ms},
        },
        "response_time_ms": round((time.time() - start) * 1000, 2),
    }

    return JSONResponse(content=payload, status_code=http_code)
