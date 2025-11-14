"""
API v1 Router Registration
"""
from fastapi import APIRouter
from app.api.v1.routers import upload, query, groups, health

router = APIRouter()

router.include_router(upload.router, prefix="/upload", tags=["upload"])
router.include_router(query.router, prefix="/query", tags=["query"])
router.include_router(groups.router, prefix="/groups", tags=["groups"])
router.include_router(health.router, prefix="/health", tags=["health"])
