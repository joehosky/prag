from __future__ import annotations

from enum import Enum as PyEnum
from typing import Optional

from pydantic import BaseModel


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


class GroupResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    uniid: str
    name: str
    status: Optional[GroupStatus] = None
    message_count: int
