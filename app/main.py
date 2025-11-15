"""
FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import router as api_router
from app.db.init_db import init_db
from app.db.alembic_runner import run_alembic_upgrade
from app.core.config import settings

# Create FastAPI instance
app = FastAPI(
    title="LINE Group RAG System",
    description="RAG system for LINE group chat analysis",
    version="0.1.0",
)

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


@app.on_event("startup")
def on_startup():
    """Run development DB initialization on startup.

    This will create missing tables based on SQLAlchemy models. Use
    Alembic for production schema migrations instead.
    """
    try:
        run_alembic_upgrade(db_url=settings.database_url)
    except Exception:
        try:
            init_db()
        except Exception:
            # in development we don't abort startup on DB issues
            pass
