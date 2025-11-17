"""FastAPI Application Entry Point"""

from contextlib import asynccontextmanager
import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import router as api_router
from app.db.alembic_runner import run_alembic_upgrade
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        run_alembic_upgrade(db_url=settings.database_url)
    except Exception:
        logging.exception("Alembic upgrade failed — aborting startup")
        raise
    yield


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
