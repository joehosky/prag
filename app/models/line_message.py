from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship

from .base import Base


class LineMessage(Base):
    __tablename__ = "line_messages"

    id = Column(Integer, primary_key=True, comment="主鍵 ID")
    group_id = Column(
        Integer,
        ForeignKey("line_groups.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
        comment="所屬群組 ID",
    )

    message_time = Column(
        DateTime(timezone=True), nullable=True, index=True, comment="訊息時間"
    )
    message_uid = Column(String(32), nullable=True, comment="所屬LINE訊息UID")
    reply_message_uid = Column(String(32), nullable=True, comment="所屬LINE訊息回覆UID")

    user_name = Column(String(64), nullable=True, comment="發送者名稱")
    user_uid = Column(String(64), nullable=True, comment="發送者名稱")

    message_content = Column(Text, nullable=True, comment="訊息原文")
    sticker = Column(String(200), nullable=True, comment="貼圖")
    link_url = Column(String(2048), nullable=True, comment="檔案連結")
    link_description = Column(Text, nullable=True, comment="描述")
    message_description = Column(Text, nullable=True, comment="處理後摘要")

    chunk_id = Column(String(100), nullable=True, index=True, comment="向量切塊 ID")
    vector_processed = Column(
        Boolean, nullable=False, default=False, comment="已送入向量化處理"
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        comment="建立時間",
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新時間",
    )

    group = relationship(
        "LineGroup", back_populates="messages", foreign_keys=[group_id], lazy="joined"
    )

    def __repr__(self) -> str:
        return f"<LineMessage id={self.id} group_id={self.group_id} message_uid={self.message_uid}>"


# indexes are declared inline; additional compound indexes can be added here if needed
