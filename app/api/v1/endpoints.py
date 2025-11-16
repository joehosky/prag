"""
API v1 Router Registration
"""

from fastapi import APIRouter
from app.api.v1.routers import messages, query, groups, health

router = APIRouter()

router.include_router(messages.router, prefix="/messages", tags=["upload"])
router.include_router(query.router, prefix="/query", tags=["query"])
router.include_router(groups.router, prefix="/groups", tags=["groups"])
router.include_router(health.router, prefix="/health", tags=["health"])
