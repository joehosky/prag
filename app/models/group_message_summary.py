from __future__ import annotations

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.line_group import LineGroup


class GroupMessageSummary(Base):
    __tablename__ = "group_message_summaries"
    __table_args__ = (
        Index("idx_group_message_time", "group_id"),
        Index("idx_message_time", "message_time"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, comment="主鍵 ID")

    group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("line_groups.id"),
        index=True,
        nullable=False,
        comment="所屬群組 ID",
    )

    message_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True, comment="訊息時間"
    )

    message_description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="處理後摘要"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        comment="建立時間",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        index=True,
        comment="更新時間",
    )

    group: Mapped[Optional["LineGroup"]] = relationship(
        "LineGroup",
        back_populates="group_message_summaries",
        foreign_keys=[group_id],
        lazy="joined",
    )
