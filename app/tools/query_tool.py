"""
Query_messages tool that can be used by multiple agents or services.
"""

from typing import Any, Dict, Optional

from app.services.query_service import QueryService


def query_messages_tool(
    group_uniid: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    top_k: int = 50,
    analysis: Optional[Dict[str, Any]] = None,
):
    """Create a query_messages tool with bound context parameters.

    The tool allows agent to override start_time/end_time for multi-range queries.

    Args:
        group_uniid: Unique identifier for the LINE group
        start_time: Default search start time (can be overridden)
        end_time: Default search end time (can be overridden)
        top_k: Maximum number of results to return
        analysis: Query analysis result (optional)

    Returns:
        LangChain tool that accepts optional time range overrides
    """
    try:
        from langchain_core.tools import tool
    except ImportError:
        from langchain.tools import tool

    @tool
    async def query_messages(
        question_text: str,
        override_start_time: Optional[str] = None,
        override_end_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Search LINE group messages for question_text.

        Args:
            question_text: Search query (natural language or keywords)
            override_start_time: Optional start time to override the default range.Format: 'YYYY-MM-DD HH:MM:SS'
            override_end_time: Optional end time to override the default range.Format: 'YYYY-MM-DD HH:MM:SS'

        Returns:
            {answer: str, items: list[dict], metadata: dict}

        Note: For multi-period queries, call multiple times with different time ranges.
        """
        svc = QueryService()

        # Use override times if provided, otherwise use default
        actual_start = override_start_time if override_start_time else start_time
        actual_end = override_end_time if override_end_time else end_time

        return await svc.query_group(
            group_uniid=group_uniid,
            question=question_text,
            start_time=actual_start,
            end_time=actual_end,
            top_k=top_k,
            analysis=analysis,
        )

    return query_messages


__all__ = ["query_messages_tool"]
