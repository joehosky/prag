from __future__ import annotations

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer
from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.line_group import LineGroup


class MessageSummaryTag(Base):
    __tablename__ = "message_summary_tags"
    __table_args__ = (Index("idx_group", "group_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, comment="主鍵 ID")

    group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("line_groups.id"),
        index=True,
        nullable=False,
        comment="所屬群組 ID",
    )

    summary_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="摘要時間"
    )

    chunk_summary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否段摘要已完成"
    )
    daily_summary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否日摘要已完成"
    )

    chunk_current_retry: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="段摘要目前重試次數"
    )
    daily_current_retry: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="日摘要目前重試次數"
    )
    chunk_max_retry: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5, comment="段摘要最大重試次數"
    )
    daily_max_retry: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5, comment="日摘要最大重試次數"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="建立時間",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        index=True,
        comment="更新時間",
    )

    group: Mapped[Optional["LineGroup"]] = relationship(
        "LineGroup",
        back_populates="message_summary_tags",
        foreign_keys=[group_id],
        lazy="joined",
    )
