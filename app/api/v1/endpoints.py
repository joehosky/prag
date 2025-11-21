"""
API v1 Router Registration
"""

from fastapi import APIRouter
from app.api.v1.routers import messages, query, groups, health, query_agent

router = APIRouter()

router.include_router(messages.router, prefix="/messages", tags=["messages"])
router.include_router(groups.router, prefix="/groups", tags=["groups"])
router.include_router(query.router, prefix="/query", tags=["query"])
router.include_router(query_agent.router, prefix="/query_agent", tags=["query_agent"])
router.include_router(health.router, prefix="/health", tags=["health"])
