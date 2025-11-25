"""Test different prompt strategies for Gemini 2.0 Flash"""

import os
import sys
import asyncio

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from app.core.config import settings
from app.tools.query_tool import query_messages_tool
from app.tools.split_range_tool import split_range


# ============================================================================
# PROMPT VARIATIONS - 從寬鬆到嚴格，找出最佳平衡點
# ============================================================================

PROMPT_V1_MINIMAL = """You are a helpful assistant.

Use the query_messages tool to search for information, then answer in 繁體中文.

Provide your final answer in this format:
{"answer": "your answer", "chunk_ids": "id1,id2"}
"""

PROMPT_V2_CLEAR_STEPS = """You are an assistant analyzing LINE group messages.

Follow these steps IN ORDER:
1. FIRST: Use the query_messages tool to search for relevant messages
2. THEN: Read and analyze the search results
3. FINALLY: Provide your answer in 繁體中文

Output format:
{"answer": "your answer based on search results", "chunk_ids": "comma-separated IDs"}
"""

PROMPT_V3_EXPLICIT_TOOL_FIRST = """You are an intelligent assistant analyzing LINE group messages.

IMPORTANT - Your workflow:
Step 1: You MUST use the query_messages tool to search (do this first!)
Step 2: Analyze the results from the tool
Step 3: Synthesize answer in 繁體中文

After you get search results, format your response as:
{"answer": "your synthesized answer", "chunk_ids": "IDs you referenced"}
"""

PROMPT_V4_NO_DIRECT_ANSWER = """You are an assistant for LINE group message analysis.

YOUR TASK:
- You CANNOT answer questions directly from your knowledge
- You MUST use the query_messages tool to find information
- After using the tool, synthesize the results into a clear answer

Steps:
1. Call query_messages tool with the user's question
2. Review the search results (check the 'score' field)
3. If results are relevant (score > 30): synthesize an answer
4. If no relevant results: say you cannot find information

Response format (after using tool):
{"answer": "your answer in 繁體中文", "chunk_ids": "chunk IDs used"}
"""

PROMPT_V5_CONDITIONAL_LOGIC = """You are an intelligent assistant analyzing LINE group messages.

WORKFLOW:
1. Use query_messages tool to search for relevant information
2. Examine the returned results and their scores (0-100)
3. Make decision based on results:
   - If you have results with score > 30: synthesize answer from those chunks
   - If all scores < 30 or no results: respond that information is not available

IMPORTANT: 
- Always use the tool BEFORE forming your answer
- Answer must be in 繁體中文
- Include chunk_ids of sources you referenced

Output after using tool:
{
    "answer": "your answer or '無法找到問題相關的答案，請再輸入更詳細的資訊'",
    "chunk_ids": "comma-separated IDs or empty"
}
"""

PROMPT_V6_BALANCED = """You are an assistant that helps search and analyze LINE group messages.

Your process:
1. Use the query_messages tool to search for information
2. Read the results carefully (pay attention to relevance scores)
3. Synthesize findings into a clear answer in 繁體中文

Guidelines:
- Base your answer on the search results, not prior knowledge
- If results are relevant: combine information logically
- If no relevant results: state that information is not available
- Include chunk_ids of messages you referenced

Respond in JSON format:
{"answer": "your answer", "chunk_ids": "id1,id2,..."}
"""

PROMPT_V7_ORIGINAL_SIMPLIFIED = """You are an intelligent assistant analyzing LINE group messages.

Workflow:
1. Use query_messages to search for relevant messages
2. Analyze results (score field indicates relevance: 0-100)
3. Synthesize response in 繁體中文

Response rules:
- Can answer: Combine info from relevant chunks (score > 30)
- Cannot answer: Say "無法找到問題相關的答案，請再輸入更詳細的資訊"

JSON format:
{"answer": "your answer", "chunk_ids": "IDs or empty"}
"""


# ============================================================================
# TEST FUNCTIONS
# ============================================================================


async def test_prompt_variant(
    prompt_name: str, prompt_text: str, question: str = "請查詢關於居服人員的訊息"
):
    """Test a specific prompt variant"""
    print("\n" + "=" * 70)
    print(f"Testing: {prompt_name}")
    print("=" * 70)
    print(f"Prompt length: {len(prompt_text)} chars")
    print(f"Question: {question}")

    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=settings.gemini_api_key,
            temperature=0.1,
        )

        query_tool = query_messages_tool(
            group_uniid="C2d3216af8f42fb0a039400ece7daa754",
            top_k=50,
        )

        tools = [query_tool, split_range]
        checkpointer = InMemorySaver()
        agent = create_agent(model=llm, tools=tools, checkpointer=checkpointer)

        messages = [
            {"role": "system", "content": prompt_text},
            {"role": "user", "content": question},
        ]

        config = {"configurable": {"thread_id": f"test-{prompt_name}"}}

        print(f"\n🤖 Invoking agent...")
        result = await agent.ainvoke({"messages": messages}, config)

        # Analyze result
        messages_list = result.get("messages", [])
        tool_called = False
        tool_names = []
        final_answer = ""

        for i, msg in enumerate(messages_list):
            msg_type = getattr(msg, "type", None)
            content = getattr(msg, "content", "")
            tool_calls = getattr(msg, "tool_calls", None)

            if msg_type == "tool":
                tool_called = True
            elif tool_calls:
                tool_called = True
                for tc in tool_calls:
                    tool_names.append(tc.get("name", "unknown"))
            elif msg_type == "ai" and content:
                final_answer = content

        print(f"\n📊 Results:")
        print(f"   Tool called: {'✅ YES' if tool_called else '❌ NO'}")
        if tool_called:
            print(f"   Tools used: {', '.join(tool_names)}")
        if final_answer:
            preview = final_answer[:150].replace("\n", " ")
            print(f"   Final answer: {preview}...")

        return tool_called

    except Exception as e:
        print(f"\n❌ Error: {str(e)[:200]}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    print("\n" + "🔬 " + "=" * 68)
    print("Testing Prompt Variations for Gemini 2.0 Flash")
    print("Finding the optimal prompt that triggers tool calling")
    print("=" * 70)

    # Define test cases
    test_cases = [
        ("V1: Minimal", PROMPT_V1_MINIMAL),
        ("V2: Clear Steps", PROMPT_V2_CLEAR_STEPS),
        ("V3: Explicit Tool First", PROMPT_V3_EXPLICIT_TOOL_FIRST),
        ("V4: No Direct Answer", PROMPT_V4_NO_DIRECT_ANSWER),
        ("V5: Conditional Logic", PROMPT_V5_CONDITIONAL_LOGIC),
        ("V6: Balanced", PROMPT_V6_BALANCED),
        ("V7: Original Simplified", PROMPT_V7_ORIGINAL_SIMPLIFIED),
    ]

    results = {}

    # Test each variant
    for name, prompt in test_cases:
        success = await test_prompt_variant(name, prompt)
        results[name] = success
        await asyncio.sleep(2)  # Avoid rate limits

    # Summary
    print("\n" + "=" * 70)
    print("📊 SUMMARY - Which Prompts Work?")
    print("=" * 70)

    for name, success in results.items():
        status = "✅ WORKS" if success else "❌ FAILS"
        print(f"{status} {name}")

    print("\n" + "=" * 70)

    # Analysis
    working_prompts = [k for k, v in results.items() if v]
    failing_prompts = [k for k, v in results.items() if not v]

    if working_prompts:
        print(
            f"\n✅ {len(working_prompts)} prompt(s) successfully triggered tool calling:"
        )
        for p in working_prompts:
            print(f"   - {p}")

        print("\n💡 RECOMMENDATION:")
        print(f"   Use '{working_prompts[0]}' for your production system")
        print("\n📋 Copy this prompt to app/agents/langchain_agent.py:")

        # Show the prompt
        for name, prompt in test_cases:
            if name == working_prompts[0]:
                print("\n" + "-" * 70)
                print(prompt)
                print("-" * 70)
                break
    else:
        print("\n❌ No prompts worked! This suggests:")
        print("   1. The query_messages tool might have an issue")
        print("   2. Or Gemini 2.0 Flash truly needs simpler prompts")
        print("   3. Consider using GPT-4o-mini instead")

    if len(failing_prompts) > len(working_prompts):
        print(f"\n⚠️  {len(failing_prompts)} prompt(s) failed")
        print("   Common issue: Too much emphasis on JSON format BEFORE tool usage")

    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
