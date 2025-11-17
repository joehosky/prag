from __future__ import annotations

from datetime import datetime
from typing import List, TYPE_CHECKING

from sqlalchemy import Index, String, Text, DateTime, Integer
import sqlalchemy as sa
from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.line_message import LineMessage
    from app.models.chunk_message_summary import ChunkMessageSummary
    from app.models.group_message_summary import GroupMessageSummary
    from app.models.message_summary_tag import MessageSummaryTag


class LineGroup(Base):
    __tablename__ = "line_groups"
    __table_args__ = (
        Index("ix_line_groups_status_created_at", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, comment="主鍵 ID")
    uniid: Mapped[str] = mapped_column(
        String(64), index=True, nullable=False, comment="群唯一碼"
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="群名")
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        index=True,
        comment="狀態 (active, inactive)",
    )
    type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="OTHER", comment="群組類別"
    )

    member_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="群組成員數"
    )
    message_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="已匯入或紀錄的訊息總數"
    )
    vector_chunks_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="與群組相關的向量切塊數量"
    )

    google_drive_folder: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="google drive的LINE群根目錄"
    )
    google_file_folder: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="google drive的LINE群檔案根目錄"
    )
    google_image_folder: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="google drive的LINE群圖片根目錄"
    )
    google_video_folder: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="google drive的LINE群影像根目錄"
    )

    available_counts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="可使用次數"
    )
    expiration_at: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="截止時間"
    )

    chunk_summary_prompt: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="訊息塊摘要的提示詞"
    )
    daily_summary_prompt: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="訊息日摘要的提示詞"
    )
    analyze_intent_prompt: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="使用者提問意圖的提示詞"
    )
    synthesize_answer_prompt: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="答案總結的提示詞"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=sa.text("now()::timestamp"),
        comment="建立時間",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=sa.text("now()::timestamp"),
        onupdate=func.now(),
        comment="更新時間",
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True, comment="軟刪除時間"
    )

    messages: Mapped[List["LineMessage"]] = relationship(
        "LineMessage",
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    chunk_message_summaries: Mapped[List["ChunkMessageSummary"]] = relationship(
        "ChunkMessageSummary",
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    group_message_summaries: Mapped[List["GroupMessageSummary"]] = relationship(
        "GroupMessageSummary",
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    message_summary_tags: Mapped[List["MessageSummaryTag"]] = relationship(
        "MessageSummaryTag",
        back_populates="group",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<LineGroup id={self.id} uniid={self.uniid} "
            f"name={self.name} status={self.status}>"
        )
