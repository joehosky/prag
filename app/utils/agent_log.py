"""Agent debug utilities."""

import logging
import time
from typing import Any, Dict, List, Optional
from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger("app.utils.agent_debug")


class DetailedTimingCallback(BaseCallbackHandler):
    """Callback that tracks detailed timing for each agent step."""

    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self._current_step = {"type": None, "start": None}

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs):
        """Called when LLM starts."""
        self._current_step = {
            "type": "llm",
            "start": time.time(),
            "model": serialized.get("name", "unknown"),
        }

    def on_llm_end(self, response, **kwargs):
        """Called when LLM ends."""
        if self._current_step["type"] == "llm":
            elapsed = time.time() - self._current_step["start"]
            self.events.append(
                {
                    "type": "llm",
                    "elapsed": elapsed,
                    "model": self._current_step.get("model", "unknown"),
                }
            )
            logger.debug("LLM completed in %.2fs", elapsed)

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs):
        """Called when tool starts."""
        self._current_step = {
            "type": "tool",
            "start": time.time(),
            "name": serialized.get("name", "unknown"),
        }

    def on_tool_end(self, output: str, **kwargs):
        """Called when tool ends."""
        if self._current_step["type"] == "tool":
            elapsed = time.time() - self._current_step["start"]
            self.events.append(
                {
                    "type": "tool",
                    "elapsed": elapsed,
                    "name": self._current_step.get("name", "unknown"),
                }
            )
            logger.debug(
                "Tool '%s' completed in %.2fs",
                self._current_step.get("name"),
                elapsed,
            )

    def on_tool_error(self, error: Exception, **kwargs):
        """Called when tool errors."""
        if self._current_step["type"] == "tool":
            elapsed = time.time() - self._current_step["start"]
            self.events.append(
                {
                    "type": "tool_error",
                    "elapsed": elapsed,
                    "name": self._current_step.get("name", "unknown"),
                    "error": str(error),
                }
            )
            logger.warning(
                "⏱️ Tool '%s' failed after %.2fs",
                self._current_step.get("name"),
                elapsed,
            )

    def get_summary(self) -> Dict[str, Any]:
        """Get timing summary."""
        llm_times = [e["elapsed"] for e in self.events if e["type"] == "llm"]
        tool_times = [e["elapsed"] for e in self.events if e["type"] == "tool"]

        return {
            "total_time": sum(llm_times) + sum(tool_times),
            "llm_time": sum(llm_times),
            "tool_time": sum(tool_times),
            "llm_count": len(llm_times),
            "tool_count": len(tool_times),
            "events": self.events,
        }

    def log_summary(self):
        """Log the timing summary."""
        summary = self.get_summary()
        logger.info("=== Timing Summary ===")
        logger.info("Total: %.2fs", summary["total_time"])
        logger.info("LLM: %.2fs (%d calls)", summary["llm_time"], summary["llm_count"])
        logger.info(
            "Tool: %.2fs (%d calls)", summary["tool_time"], summary["tool_count"]
        )
        logger.info("=== End Summary ===")


def log_agent_result(
    result: Dict[str, Any],
    enabled: bool = True,
    log_level: str = "INFO",
) -> None:
    """Log agent result messages for debugging."""
    if not enabled:
        return

    log_func = getattr(logger, log_level.lower(), logger.info)
    messages = result.get("messages", [])

    log_func("=== Agent Messages (%d total) ===", len(messages))

    for i, msg in enumerate(messages):
        msg_type = getattr(msg, "type", type(msg).__name__)
        content = getattr(msg, "content", "")
        tool_calls = getattr(msg, "tool_calls", None)

        content_preview = str(content)[:150] if content else "empty"
        if len(str(content)) > 150:
            content_preview += "..."

        log_func(
            "Message[%d] type=%s tool_calls=%s content=%s",
            i,
            msg_type,
            tool_calls if tool_calls else None,
            content_preview,
        )

    log_func("=== End Messages ===")
