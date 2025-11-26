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
    timing_callback: Optional["DetailedTimingCallback"] = None,
) -> None:
    """Log agent result messages for debugging.

    Args:
        result: Agent result dictionary containing messages
        enabled: Whether logging is enabled
        log_level: Log level (INFO, DEBUG, etc.)
        timing_callback: Optional timing callback to show execution time per message
    """
    if not enabled:
        return

    log_func = getattr(logger, log_level.lower(), logger.info)
    messages = result.get("messages", [])

    # Get timing events if available
    events = []
    if timing_callback:
        events = timing_callback.events

    # Track which event we're on
    llm_event_idx = 0
    tool_event_idx = 0

    log_func("=== Agent Messages (%d total) ===", len(messages))

    # Icon mapping for message types (bright colors for dark theme)
    type_icons = {
        "system": "⚙️ ",
        "human": "👤",
        "ai": "🤖",
        "assistant": "🤖",
        "tool": "🔧",
    }

    for i, msg in enumerate(messages):
        msg_type = getattr(msg, "type", type(msg).__name__)
        content = getattr(msg, "content", "")
        tool_calls = getattr(msg, "tool_calls", None)

        content_preview = str(content)[:150] if content else "empty"
        if len(str(content)) > 150:
            content_preview += "..."

        # Get icon for message type
        icon = type_icons.get(msg_type, "📝")

        # Find corresponding timing for this message
        timing_str = ""
        if timing_callback and events:
            # AI messages with tool_calls or content correspond to LLM calls
            if msg_type in ("ai", "assistant"):
                if tool_calls:
                    # This is an LLM call that decided to use tools
                    llm_events = [e for e in events if e["type"] == "llm"]
                    if llm_event_idx < len(llm_events):
                        elapsed = llm_events[llm_event_idx]["elapsed"]
                        timing_str = f"\033[91m ⏱️ {elapsed:.2f}s\033[0m"
                        llm_event_idx += 1
                elif content:
                    # This is the final LLM response
                    llm_events = [e for e in events if e["type"] == "llm"]
                    if llm_event_idx < len(llm_events):
                        elapsed = llm_events[llm_event_idx]["elapsed"]
                        timing_str = f"\033[91m ⏱️ {elapsed:.2f}s\033[0m"
                        llm_event_idx += 1

            # Tool messages correspond to tool calls
            elif msg_type == "tool":
                tool_events = [e for e in events if e["type"] in ("tool", "tool_error")]
                if tool_event_idx < len(tool_events):
                    event = tool_events[tool_event_idx]
                    elapsed = event["elapsed"]
                    timing_str = f"\033[91m ⏱️ {elapsed:.2f}s\033[0m"
                    if event["type"] == "tool_error":
                        timing_str += " ❌"
                    tool_event_idx += 1

        log_func(
            "Message[%d] %s type=%s%s tool_calls=%s content=%s",
            i,
            icon,
            msg_type,
            timing_str,
            tool_calls if tool_calls else None,
            content_preview,
        )

    log_func("=== End Messages ===")
