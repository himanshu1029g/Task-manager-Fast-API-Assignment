import logging
import logging.config
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import create_tables
from app.cache import close_redis
from app.routers import health, tasks, ai

# ── Structured Logging ────────────────────────────────────────────────────────
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
            "stream": "ext://sys.stdout",
        }
    },
    "root": {"level": "INFO", "handlers": ["console"]},
    "loggers": {
        "uvicorn.access": {"level": "INFO", "handlers": ["console"], "propagate": False},
        "uvicorn.error":  {"level": "INFO", "handlers": ["console"], "propagate": False},
        "sqlalchemy.engine": {"level": "WARNING", "propagate": True},
    },
}
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


# ── Lifespan (startup / shutdown) ────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup | Task Manager API initialising | env=%s", settings.APP_ENV)
    try:
        await create_tables()
        logger.info("startup | Database tables ready")
    except Exception as exc:
        logger.critical("startup | Database init failed: %s", exc, exc_info=True)
        raise
    yield
    logger.info("shutdown | Closing Redis connection...")
    await close_redis()
    logger.info("shutdown | Clean exit")


# ── App init ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Task Manager API",
    description="Production-ready FastAPI with PostgreSQL, Redis & Gemini AI",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    # Hide detailed error info from clients in production
    openapi_url="/openapi.json" if settings.APP_ENV != "production" else "/openapi.json",
)

# ── CORS — restrict to known origins in production ───────────────────────────
# Set ALLOWED_ORIGINS in .env for production (e.g. https://yourdomain.com)
# Falls back to wildcard only when APP_ENV is not 'production'
_origins = (
    [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
    if settings.ALLOWED_ORIGINS
    else (["*"] if settings.APP_ENV != "production" else [])
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,       # Do not allow credentials with wildcard
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# ── Global exception handler — no stack traces leaked to clients ──────────────
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(
        "unhandled_exception | %s %s | %s: %s",
        request.method, request.url.path,
        type(exc).__name__, exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(tasks.router)
app.include_router(ai.router)

# ── Static files (MUST be last — catches everything else) ────────────────────
app.mount("/", StaticFiles(directory="static", html=True), name="static")
