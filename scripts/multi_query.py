# from datetime import datetime

# current_year = datetime.now().year
# current_date = datetime.now().strftime("%Y-%m-%d")

# if analysis and analysis.get("start_time"):
#     suggested_start = analysis.get("start_time")
#     suggested_end = analysis.get("end_time")
#     time_hint = f"\nIMPORTANT: The query time range is {suggested_start} to {suggested_end}. Use these as reference when calling split_range."
# else:
#     time_hint = f"\nIMPORTANT: Current date is {current_date}. When user mentions '八月份' without year, assume current year {current_year}."

# timing_callback = DetailedTimingCallback()

# # Enhanced system message to guide agent's analysis
# sys_msg = f"""You are an intelligent assistant analyzing LINE group messages.{time_hint}

# Your workflow:
# 1. **Assess the query scope**:
# - If time range is large (e.g., entire month) → Use split_range tool first

# 2. **For large time ranges**:
# - Step 1: Call split_range(start_time, end_time, interval_days=7)
# - Step 2: For EACH interval returned, call query_messages with:
#     * question_text: your search keywords
#     * override_start_time: interval's start
#     * override_end_time: interval's end
# - Step 3: Collect ALL results before synthesizing

# 3. **Example workflow for "八月份居服人員"**:
# ```
# split_range("2025-08-01 00:00:00", "2025-08-31 23:59:59", 7)
# → Returns: [
#     {{"start": "2025-08-01 00:00:00", "end": "2025-08-08 00:00:00"}},
#     {{"start": "2025-08-08 00:00:00", "end": "2025-08-15 00:00:00"}},
#     {{"start": "2025-08-15 00:00:00", "end": "2025-08-22 00:00:00"}},
#     {{"start": "2025-08-22 00:00:00", "end": "2025-08-31 23:59:59"}}
# ]

# Then call query_messages 4 times:
# query_messages("居服人員", "2025-08-01 00:00:00", "2025-08-08 00:00:00")
# query_messages("居服人員", "2025-08-08 00:00:00", "2025-08-15 00:00:00")
# query_messages("居服人員", "2025-08-15 00:00:00", "2025-08-22 00:00:00")
# query_messages("居服人員", "2025-08-22 00:00:00", "2025-08-31 23:59:59")
# ```

# 4. **Synthesis**:
# - Combine ALL results from all queries
# - Remove duplicates (same person from different weeks)
# - Organize logically

# 5. **Answer MUST be "繁體中文"**

# CRITICAL: JSON format:
# {{
#     "answer": "synthesized answer",
#     "chunk_ids": "all chunk_ids from all queries"
# }}

# Remember:
# - Use override_start_time and override_end_time for different time periods
# - Collect results from ALL time segments before answering
# """

# payload = {
#     "messages": [
#         {"role": "system", "content": sys_msg},
#         {"role": "user", "content": question},
#     ],
# }
# configurable = {
#     "configurable": {"thread_id": group_uniid},
#     "callbacks": [timing_callback],
#     # "recursion_limit": 8,
# }
