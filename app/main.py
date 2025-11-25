"""FastAPI Application Entry Point"""

from contextlib import asynccontextmanager
import logging
import traceback
import sys
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.logging import setup_logging

setup_logging()
logging.getLogger().info("Starting app with python: %s", sys.executable)

from app.api.v1.endpoints import router as api_router
from app.db.alembic_runner import run_alembic_upgrade
from app.core.config import settings
from app.services.bm25_service import get_bm25_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("Application startup")
    logger.info("=" * 60)

    try:
        logger.info("Running Alembic migrations...")
        run_alembic_upgrade(db_url=settings.database_url)
        logger.info("Alembic migrations completed")
    except Exception:
        logger.exception("Alembic upgrade failed — aborting startup")
        raise

    try:
        logger.info("Preloading BM25 service...")
        start_time = time.time()

        bm25_service = get_bm25_service()
        elapsed = time.time() - start_time

        logger.info(
            f"BM25 service preloaded: {len(bm25_service.docs)} documents in {elapsed:.2f}s"
        )

    except Exception as e:
        logger.exception(f"Failed to preload BM25 service: {e}")

    logger.info("=" * 60)
    logger.info("Application startup complete - Ready to serve requests")
    logger.info("=" * 60)

    yield

    logger.info("Application shutdown")


# Create FastAPI instance with lifespan
app = FastAPI(
    title="LINE Group RAG System",
    description="RAG system for LINE group chat analysis",
    version="0.1.0",
    lifespan=lifespan,
)

logger = logging.getLogger("app")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "Unhandled exception while processing %s %s", request.method, request.url
    )
    if getattr(settings, "app_env", "development") == "development":
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "traceback": traceback.format_exc()},
        )
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "LINE Group RAG System API", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
