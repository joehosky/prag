from __future__ import annotations

from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    func,
)
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.line_group import LineGroup


class ChunkMessageSummary(Base):
    __tablename__ = "chunk_message_summaries"
    __table_args__ = (
        Index("idx_group_time", "group_id"),
        Index("idx_group_time_range", "group_id", "start_time", "end_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="主鍵 ID")
    chunk_id: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="向量切塊ID"
    )
    group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("line_groups.id"),
        index=True,
        nullable=False,
        comment="所屬群組 ID",
    )

    start_time: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=False), nullable=False, comment="片段開始時間"
    )
    end_time: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=False), nullable=False, comment="片段結束時間"
    )

    message_ids: Mapped[Optional[str]] = mapped_column(
        String(1024), nullable=True, comment="訊息 id 列表（如1,3,12,16），可為空"
    )
    message_content: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="處理前訊息"
    )
    message_summary: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="處理後摘要"
    )

    qdrant_point_id: Mapped[Optional[str]] = mapped_column(
        String(100), index=True, nullable=True, comment="Qdrant point id"
    )

    # Embedding stored as JSON array of floats
    embedding: Mapped[Optional[List[float]]] = mapped_column(
        JSON, nullable=True, comment="Embedding vector"
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=False),
        server_default=sa.text("now()::timestamp"),
        nullable=False,
        comment="建立時間",
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=False),
        server_default=sa.text("now()::timestamp"),
        onupdate=func.now(),
        index=True,
        comment="更新時間",
    )

    # Relationship to the group (assumes `LineGroup` / `line_groups` exists)
    group: Mapped[Optional["LineGroup"]] = relationship(
        "LineGroup", back_populates="chunk_message_summaries"
    )
