from __future__ import annotations

import json
import logging
import time
from typing import List, Dict, Any, Optional

import openai

from app.core.config import settings

logger = logging.getLogger(__name__)


def call_llm(
    prompt: str,
    snippets: List[str],
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
    openai.api_key = api_key

    model_name = model or settings.openai_model

    # combine snippets into a single JSON string payload
    try:
        snippets_json = json.dumps(snippets, ensure_ascii=False)
    except Exception:
        # fallback: join by newline
        snippets_json = "\n\n".join(snippets)

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": snippets_json},
    ]

    attempt = 0
    backoff = 0.5
    while True:
        try:
            # openai Python SDK supports request_timeout
            resp = openai.ChatCompletion.create(
                model=model_name,
                messages=messages,
                max_tokens=max_tokens,
                request_timeout=timeout,
            )
            # response format may vary; extract text
            if "choices" in resp and len(resp.choices) > 0:
                text = (
                    resp.choices[0].message.get("content")
                    if hasattr(resp.choices[0], "message")
                    else resp.choices[0].get("text")
                )
                if text is None:
                    # try converting whole resp
                    text = json.dumps(resp)
                return text
            # fallback stringify
            return str(resp)
        except Exception as e:
            attempt += 1
            logger.exception("LLM call failed on attempt %d: %s", attempt, e)
            if attempt > retries:
                raise
            time.sleep(backoff)
            backoff *= 2


def parse_llm_topics(raw: str) -> List[Dict[str, Any]]:
    """Robustly extract a JSON array of topic objects from raw LLM output.

    Tries direct json.loads first; if that fails, finds first `[` and last `]` and
    attempts to parse the slice.
    """
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
        # if it's a dict with a top-level key containing the array, try to find it
        for v in parsed.values() if isinstance(parsed, dict) else []:
            if isinstance(v, list):
                return v
    except Exception:
        pass

    # try to extract first JSON array in the text
    sidx = raw.find("[")
    eidx = raw.rfind("]")
    if sidx >= 0 and eidx > sidx:
        cand = raw[sidx : eidx + 1]
        try:
            parsed = json.loads(cand)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            logger.exception("Failed to parse candidate JSON array from LLM output")

    # as last resort, return empty
    logger.warning("No JSON array found in LLM output; returning empty list")
    return []


__all__ = ["call_llm", "parse_llm_topics"]
