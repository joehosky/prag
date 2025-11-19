"""
LINE Groups Management Router
"""

import logging

from typing import List, Dict
from enum import Enum as PyEnum

from app.schemas.groups import (
    CreateGroupRequest,
    UpdateGroupRequest,
    GroupStatus,
    GroupResponse,
)

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.group_service import GroupService


router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[GroupResponse])
def list_groups(db: Session = Depends(get_db)):
    logger.info("List all group request received: %s", "test")

    """List active LINE groups"""
    svc = GroupService()
    groups = svc.list_active(db)
    logger.debug("Qyert group from DB")

    return [GroupResponse.model_validate(g) for g in groups]


@router.get("/{group_id}", response_model=GroupResponse)
def get_group(group_id: str, db: Session = Depends(get_db)):
    """Get specific group details by id"""
    svc = GroupService()
    grp = svc.get_by_id(db, group_id)
    if not grp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Group not found"
        )
    return GroupResponse.model_validate(grp)


@router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(payload: CreateGroupRequest, db: Session = Depends(get_db)):
    """Create a new LINE group"""
    svc = GroupService()
    status_val = payload.status.value if payload.status is not None else None
    obj = svc.create_group(
        db, uniid=payload.uniid, name=payload.name, status=status_val
    )
    db.commit()
    db.refresh(obj)
    return GroupResponse.model_validate(obj)


@router.put("/{group_id}", response_model=GroupResponse)
def update_group(
    group_id: str, payload: UpdateGroupRequest, db: Session = Depends(get_db)
):
    """Update an existing group by id"""
    svc = GroupService()
    grp = svc.get_by_id(db, group_id)
    if not grp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Group not found"
        )

    raw = payload.model_dump(exclude_none=True)
    for k, v in raw.items():
        if isinstance(v, PyEnum):
            raw[k] = v.value

    updates = raw
    obj = svc.update_group(db, grp, updates)
    db.commit()
    db.refresh(obj)
    return GroupResponse.model_validate(obj)
