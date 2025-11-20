"""Package initialization

Import model modules so SQLAlchemy mappers are registered when the
package is imported. This prevents mapper-initialization errors where a
relationship references a class that has not yet been imported.
"""

from app.models.base import Base

# Ensure all model modules are imported and mappers are configured
from app.models.chunk_message_summary import ChunkMessageSummary
from app.models.group_message_summary import GroupMessageSummary
from app.models.line_group import LineGroup
from app.models.line_message import LineMessage
from app.models.message_summary_tag import MessageSummaryTag

__all__ = [
    "Base",
    "ChunkMessageSummary",
    "GroupMessageSummary",
    "LineGroup",
    "LineMessage",
    "MessageSummaryTag",
]
