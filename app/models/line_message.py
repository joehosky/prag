from __future__ import annotations

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Integer, String, Text, DateTime, Boolean, ForeignKey
import sqlalchemy as sa
from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.line_group import LineGroup


class LineMessage(Base):
    __tablename__ = "line_messages"

    id: Mapped[int] = mapped_column(primary_key=True, comment="主鍵 ID")

    group_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("line_groups.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        comment="所屬群組 ID",
    )

    message_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True, index=True, comment="訊息時間"
    )
    message_uid: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="所屬LINE訊息UID"
    )
    reply_message_uid: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="所屬LINE訊息回覆UID"
    )

    user_name: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="發送者名稱"
    )
    user_uid: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="發送者 UID"
    )

    message_content: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="訊息原文"
    )
    sticker: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="貼圖"
    )
    link_url: Mapped[str | None] = mapped_column(
        String(2048), nullable=True, comment="檔案連結"
    )
    link_description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="描述"
    )
    message_description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="處理後摘要"
    )

    chunk_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True, comment="向量切塊 ID"
    )
    vector_processed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="已送入向量化處理"
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

    group: Mapped[Optional["LineGroup"]] = relationship(
        "LineGroup",
        back_populates="messages",
        foreign_keys=[group_id],
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<LineMessage id={self.id} group_id={self.group_id} message_uid={self.message_uid}>"
