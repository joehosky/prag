"""Test Gemini tool calling directly."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from app.core.config import settings


class SearchInput(BaseModel):
    query: str = Field(description="The search query")


@tool("search_messages", args_schema=SearchInput)
def search_messages(query: str) -> str:
    """Search for messages in the LINE group."""
    return f"Found results for: {query}"


def test_direct_bind_tools():
    """Test bind_tools directly without agent."""
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=settings.gemini_api_key,
    )

    tools = [search_messages]
    llm_with_tools = llm.bind_tools(tools)

    # 測試 1: 一般問題
    print("=== Test 1: Direct question ===")
    response = llm_with_tools.invoke("搜尋關於遊戲問題的訊息")
    print(f"Content: {response.content[:100] if response.content else 'empty'}")
    print(f"Tool calls: {response.tool_calls}")

    # 測試 2: 明確要求使用工具
    print("\n=== Test 2: Explicit tool request ===")
    response2 = llm_with_tools.invoke("請使用 search_messages 工具搜尋「億萬富翁遊戲」")
    print(f"Content: {response2.content[:100] if response2.content else 'empty'}")
    print(f"Tool calls: {response2.tool_calls}")

    # 測試 3: 用 tool_choice 強制
    print("\n=== Test 3: Force tool_choice ===")
    try:
        llm_forced = llm.bind_tools(tools, tool_choice="any")
        response3 = llm_forced.invoke("億萬富翁的遊戲使用上有遇到什麼問題嗎?")
        print(f"Content: {response3.content[:100] if response3.content else 'empty'}")
        print(f"Tool calls: {response3.tool_calls}")
    except Exception as e:
        print(f"tool_choice='any' failed: {e}")

        # 嘗試其他 tool_choice 格式
        try:
            llm_forced2 = llm.bind_tools(
                tools,
                tool_choice={
                    "type": "function",
                    "function": {"name": "search_messages"},
                },
            )
            response4 = llm_forced2.invoke("億萬富翁的遊戲使用上有遇到什麼問題嗎?")
            print(
                f"Content: {response4.content[:100] if response4.content else 'empty'}"
            )
            print(f"Tool calls: {response4.tool_calls}")
        except Exception as e2:
            print(f"dict tool_choice also failed: {e2}")


if __name__ == "__main__":
    test_direct_bind_tools()
