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
        """Search and retrieve relevant LINE messages based on the question.

        This tool performs semantic search through the LINE group's message history
        to find the most relevant messages matching the given question.

        Args:
            question_text: The search query or question. Use natural language or
                        keywords to describe what you're looking for.
            override_start_time: Optional start time to override the default range.
                                Format: 'YYYY-MM-DD HH:MM:SS'
            override_end_time: Optional end time to override the default range.
                              Format: 'YYYY-MM-DD HH:MM:SS'

        Returns:
            A dictionary containing:
            - answer: A string containing all matched chunk messages
            - items: A list of match details with chunk_id, score, and text
            - metadata: Additional search information

        Important notes:
            - Results are ranked by relevance score (highest first)
            - Scores above 80 indicate highly relevant matches
            - Use override_start_time/override_end_time for querying specific time ranges
            - When querying multiple time periods, call this tool multiple times with
              different time overrides

        Example for multi-period query:
            # Query week 1 of August
            query_messages(
                question_text="居服人員",
                override_start_time="2025-08-01 00:00:00",
                override_end_time="2025-08-07 23:59:59"
            )

            # Query week 2 of August
            query_messages(
                question_text="居服人員",
                override_start_time="2025-08-08 00:00:00",
                override_end_time="2025-08-14 23:59:59"
            )
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
