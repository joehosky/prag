from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.agents.llm_manager import get_llm_manager

logger = logging.getLogger(__name__)


def _default_analysis(question: str) -> Dict[str, Any]:
    return {
        "queryType": "general",
        "startTime": None,
        "endTime": None,
        "resolvedQuery": question,
        "keywords": [],
    }


def analyze_query(
    question: str,
    history: Optional[List[Dict[str, Any]]] = None,
    now_str: Optional[str] = None,
) -> Dict[str, Any]:
    """Analyze the user's question using LangChain."""

    ctx_text = ""
    if history:
        try:
            parts = []
            for h in history:
                if isinstance(h, dict):
                    parts.append(h.get("content") or h.get("text") or str(h))
                else:
                    parts.append(str(h))
            ctx_text = "\n".join([p for p in parts if p])
        except Exception:
            ctx_text = str(history)

    prompt = f"""
分析查詢並輸出 JSON。當前時間：{now_str}

問題：{question}
歷史對話：{ctx_text}

輸出格式：
{{"queryType":"QueryTypeSemantics|QueryTypeExact|QueryTypeRecent","startTime":"YYYY-MM-DD HH:MM:SS或null","endTime":"YYYY-MM-DD HH:MM:SS或null","resolvedQuery":"改寫查詢","keywords":[{{"text":"詞","required":true/false}}]}}

queryType 規則：
- QueryTypeExact：有人名/公司名/產品名/明確日期/特定編號
- QueryTypeRecent：有"今天/昨天/最近/這周"等時間詞，或範圍≤30天
- QueryTypeSemantics：其他情況
優先級：Exact > Recent > Semantics

時間轉換（台北時區，周一為首日）：
今天→00:00-23:59｜昨天→前一天｜這周→周一至周日｜上周→上周一至周日｜這個月→1日至月底｜最近→7天前至今｜無時間詞→null

改寫規則（重要）：
1. 必須從歷史對話提取實體替換代詞（他/她/它/這個/那個/第一個/也/還等）
2. 移除時間詞（已在 startTime/endTime）
3. 保留核心關鍵詞
4. 如果問題中有代詞，必須從歷史找到對應實體

關鍵詞：最多3個，實體required=true、屬性false、無則[]

純JSON輸出，無markdown。
"""

    try:
        llm_manager = get_llm_manager()
        raw = llm_manager.invoke(prompt, max_tokens=1024)

        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        parsed = json.loads(raw)
        return {
            "queryType": parsed.get("queryType") or "general",
            "startTime": parsed.get("startTime"),
            "endTime": parsed.get("endTime"),
            "resolvedQuery": parsed.get("resolvedQuery") or question,
            "keywords": parsed.get("keywords") or [],
        }
    except Exception:
        logger.exception("LLM analysis failed, using default")
        return _default_analysis(question)


__all__ = ["analyze_query"]
