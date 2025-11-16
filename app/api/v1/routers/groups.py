"""
LINE Groups Management Router
"""

from typing import List, Dict, Optional
from enum import Enum as PyEnum

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.group_service import GroupService

router = APIRouter()


class GroupStatus(str, PyEnum):
    active = "active"
    inactive = "inactive"


class CreateGroupRequest(BaseModel):
    uniid: str
    name: str
    status: Optional[GroupStatus] = None


class UpdateGroupRequest(BaseModel):
    name: Optional[str] = None
    status: Optional[GroupStatus] = None


def _group_to_dict(g) -> Dict:
    return {
        "id": g.id,
        "uniid": g.uniid,
        "name": g.name,
        "status": g.status,
        "message_count": g.message_count,
    }


@router.get("/", response_model=List[Dict])
def list_groups(db: Session = Depends(get_db)):
    """List active LINE groups"""
    svc = GroupService()
    groups = svc.list_active(db)
    return [_group_to_dict(g) for g in groups]


@router.get("/{group_uni_id}")
def get_group(group_id: str, db: Session = Depends(get_db)):
    """Get specific group details by id"""
    svc = GroupService()
    grp = svc.get_by_id(db, group_id)
    if not grp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Group not found"
        )
    return _group_to_dict(grp)


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_group(payload: CreateGroupRequest, db: Session = Depends(get_db)):
    """Create a new LINE group"""
    svc = GroupService()
    status_val = payload.status.value if payload.status is not None else None
    obj = svc.create_group(
        db, uniid=payload.uniid, name=payload.name, status=status_val
    )
    db.commit()
    db.refresh(obj)
    return _group_to_dict(obj)


@router.put("/{group_id}")
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
    return _group_to_dict(obj)
