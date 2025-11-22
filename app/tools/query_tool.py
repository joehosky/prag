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

    This factory function creates a LangChain tool that has already bound
    the group_uniid, start_time, end_time, top_k, and analysis parameters,
    so the LLM only needs to provide the question_text parameter.

    Args:
        group_uniid: Unique identifier for the LINE group
        start_time: Search start time (optional)
        end_time: Search end time (optional)
        top_k: Maximum number of results to return
        analysis: Query analysis result (optional)

    Returns:
        LangChain tool with bound context parameters

    Example:
        >>> tool = query_messages_tool(
        ...     group_uniid="group_abc123",
        ...     top_k=10
        ... )
        >>> # Use in agent
        >>> agent = create_agent(model=llm, tools=[tool])
    """
    try:
        from langchain_core.tools import tool
    except ImportError:
        from langchain.tools import tool

    @tool
    async def query_messages(question_text: str) -> Dict[str, Any]:
        """Search and retrieve relevant LINE messages based on the question.

        This tool performs semantic search through the LINE group's message history
        to find the most relevant messages matching the given question.

        Args:
            question_text: The search query or question. Use natural language or
                        keywords to describe what you're looking for.

        Returns:
            A dictionary containing:
            - answer: A string containing all matched chunk messages, separated by
                    double newlines (\\n\\n). Each segment is a message chunk that
                    matches the query.
            - items: A list of match details, where each item contains:
              * chunk_id: Unique identifier for the message chunk
              * score: Relevance score (0 to 100, higher is more relevant)
              * text: The actual message content (corresponds to a segment in 'answer')
            - metadata: Additional search information (optional)

        Important notes:
            - Results are ranked by relevance score (highest first)
            - Scores above 80 indicate highly relevant matches
            - Scores between 60-80 are moderately relevant
            - Scores below 60 may not be very relevant
            - The 'answer' field contains all messages concatenated for easy reading
            - The 'items' field provides structured data with scores for each chunk
            - Use high-scoring items (score > 70) for the most accurate information

        Example return structure:
            {
                "answer": "First message chunk\\n\\nSecond message chunk\\n\\nThird chunk",
                "items": [
                    {"chunk_id": "msg_001", "score": 95, "text": "First message chunk"},
                    {"chunk_id": "msg_002", "score": 88, "text": "Second message chunk"},
                    {"chunk_id": "msg_003", "score": 75, "text": "Third chunk"}
                ],
                "metadata": {...}
            }
        """
        svc = QueryService()

        return await svc.query_group(
            group_uniid=group_uniid,
            question=question_text,
            start_time=start_time,
            end_time=end_time,
            top_k=top_k,
            analysis=analysis,
        )

    return query_messages


__all__ = ["query_messages_tool"]
