from __future__ import annotations

"""
This module is intentionally small and safe: it tries to use the application's
OpenAI-like client when available and otherwise provides a deterministic
fallback so the app can start and tests can run.
"""

from typing import Any, Dict, List, Optional
import json
import logging
import time

from openai import OpenAI
from app.core.config import settings

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
    """Analyze the user's question and return a small JSON-able dict.

    The preferred behavior is to call the configured LLM. If that fails,
    return a conservative default analysis.
    """
    api_key = settings.openai_api_key
    if not api_key:
        return _default_analysis(question)

    try:
        client = OpenAI(api_key=api_key)
    except Exception:
        logger.exception("Failed to construct OpenAI client")
        return _default_analysis(question)

    # build history/context text
    ctx_text = ""
    if history:
        try:
            # history is expected to be a list of dicts with 'content' or similar
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

範例：

例1（基本查詢）：
問：悠勢科技統編
→{{"queryType":"QueryTypeExact","startTime":null,"endTime":null,"resolvedQuery":"悠勢科技 統編","keywords":[{{"text":"悠勢科技","required":true}},{{"text":"統編","required":true}}]}}

例2（時間查詢）：
問：今天重要訊息
→{{"queryType":"QueryTypeRecent","startTime":"2025-10-28 00:00:00","endTime":"2025-10-28 23:59:59","resolvedQuery":"重要訊息","keywords":[{{"text":"重要","required":false}}]}}

例3（代詞補充-關鍵）：
歷史：用戶問評估人員李孟憲的聯絡方式｜問：給我他在九月份服務過的個案資料
→{{"queryType":"QueryTypeExact","startTime":"2025-09-01 00:00:00","endTime":"2025-09-30 23:59:59","resolvedQuery":"李孟憲 服務過的個案資料","keywords":[{{"text":"李孟憲","required":true}},{{"text":"個案資料","required":true}}]}}

例4（代詞補充-第一個）：
歷史：用戶問最近餐廳，助手回建弘雞肉飯和合麟料理｜問：第一個的地址
→{{"queryType":"QueryTypeExact","startTime":null,"endTime":null,"resolvedQuery":"建弘雞肉飯 地址","keywords":[{{"text":"建弘雞肉飯","required":true}},{{"text":"地址","required":true}}]}}

例5（代詞補充-它/這個）：
歷史：用戶問悠勢科技統編，助手回52492792｜問：它的電話也給我
→{{"queryType":"QueryTypeExact","startTime":null,"endTime":null,"resolvedQuery":"悠勢科技 電話","keywords":[{{"text":"悠勢科技","required":true}},{{"text":"電話","required":true}}]}}

純JSON輸出，無markdown。
"""

    try:
        raw = call_llm(prompt, max_tokens=1024)
        parsed = json.loads(raw)
        return {
            "queryType": parsed.get("queryType") or "general",
            "startTime": parsed.get("startTime"),
            "endTime": parsed.get("endTime"),
            "resolvedQuery": parsed.get("resolvedQuery") or question,
            "keywords": parsed.get("keywords") or [],
        }
    except Exception:
        logger.debug("LLM analysis failed or returned non-JSON, using default")
        return _default_analysis(question)


def call_llm(
    prompt: str,
    snippets: Optional[List[str]] = None,
    model: Optional[str] = None,
    timeout: int = 120,
    retries: int = 2,
    max_tokens: int = 12000,
) -> str:
    """Call OpenAI ChatCompletion with prompt + snippets.

    Returns raw text response. Retries on transient errors with exponential backoff.
    """
    api_key = settings.openai_api_key
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured in settings")

    model_name = model or settings.openai_model
    client = OpenAI(api_key=api_key)

    try:
        snippets_json = (
            json.dumps(snippets, ensure_ascii=False) if snippets is not None else ""
        )
    except Exception:
        snippets_json = "\n\n".join(snippets) if snippets is not None else ""

    if snippets_json:
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": snippets_json},
        ]
    else:
        messages = [{"role": "user", "content": prompt}]

    attempt = 0
    backoff = 0.5
    while True:
        try:
            resp = client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=max_tokens,
                timeout=timeout,
            )

            # response format: resp.choices -> list with .message.content
            if hasattr(resp, "choices") and len(resp.choices) > 0:
                first = resp.choices[0]
                msg = getattr(first, "message", None)
                if msg and getattr(msg, "content", None) is not None:
                    return msg.content

            return json.dumps(resp, default=str)
        except Exception as e:
            attempt += 1
            logger.exception("LLM call failed on attempt %d: %s", attempt, e)
            if attempt > retries:
                raise
            time.sleep(backoff)
            backoff *= 2


def parse_llm_topics(raw: str) -> List[Dict[str, Any]]:
    """Attempt to parse LLM output into a list of topic dicts.

    Expected JSON shape is a list of objects like:
    [{"detail": "...", "ids": [1,2], "startTime": "...", "endTime": "..."}]

    If parsing fails, return an empty list.
    """
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
        for v in parsed.values() if isinstance(parsed, dict) else []:
            if isinstance(v, list):
                return v
        return []
    except Exception:
        logger.debug("parse_llm_topics: failed to parse raw output as JSON")
        return []


__all__ = ["analyze_query", "call_llm", "parse_llm_topics"]
