from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Index,
)
from sqlalchemy.orm import relationship

from .base import Base


class LineGroup(Base):
    __tablename__ = "line_groups"

    id = Column(Integer, primary_key=True, comment="主鍵 ID")
    uniid = Column(String(64), index=True, nullable=False, comment="群唯一碼")
    name = Column(String(255), nullable=False, comment="群名")
    status = Column(
        String(20),
        nullable=False,
        default="active",
        index=True,
        comment="狀態 (active, inactive)",
    )
    type = Column(String(32), nullable=False, default="OTHER", comment="群組類別")

    member_count = Column(Integer, nullable=False, default=0, comment="群組成員數")
    message_count = Column(
        Integer, nullable=False, default=0, comment="已匯入或紀錄的訊息總數"
    )
    vector_chunks_count = Column(
        Integer, nullable=False, default=0, comment="與群組相關的向量切塊數量"
    )

    google_drive_folder = Column(
        String(64), nullable=True, comment="google drive的LINE群根目錄"
    )
    google_file_folder = Column(
        String(64), nullable=True, comment="google drive的LINE群檔案根目錄"
    )
    google_image_folder = Column(
        String(64), nullable=True, comment="google drive的LINE群圖片根目錄"
    )
    google_video_folder = Column(
        String(64), nullable=True, comment="google drive的LINE群影像根目錄"
    )

    available_counts = Column(Integer, nullable=False, default=0, comment="可使用次數")
    expiration_at = Column(String(32), nullable=True, comment="截止時間")

    chunk_summary_prompt = Column(Text, nullable=True, comment="訊息塊摘要的提示詞")
    daily_summary_prompt = Column(Text, nullable=True, comment="訊息日摘要的提示詞")
    analyze_intent_prompt = Column(
        Text, nullable=True, comment="使用者提問意圖的提示詞"
    )
    synthesize_answer_prompt = Column(Text, nullable=True, comment="答案總結的提示詞")

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
    deleted_at = Column(DateTime(timezone=True), nullable=True, comment="軟刪除時間")

    messages = relationship(
        "LineMessage",
        back_populates="group",
        passive_deletes=True,
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<LineGroup id={self.id} uniid={self.uniid} name={self.name} status={self.status}>"


# composite index similar to GORM's idx_status_created (status, created_at)
Index("idx_status_created", LineGroup.status, LineGroup.created_at)
