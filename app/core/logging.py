"""Application logging configuration.

Environment variables (defaults):
- LOG_LEVEL: root log level (INFO)
- LOG_CONSOLE: 'true'|'false' (true)
- LOG_CONSOLE_LEVEL: console level (inherits LOG_LEVEL)
- LOG_FILE: 'true'|'false' (false)
- LOG_FILE_LEVEL: file level (inherits LOG_LEVEL)
- LOG_DIR: directory to write logs ('logs')
- LOG_RETENTION_DAYS: int days to keep (7)

Usage:
    from app.core.logging import setup_logging
    setup_logging()

This module avoids external dependencies and implements an "hourly" file
handler that rotates the target filename every hour by creating a new file
path in the day folder (e.g. logs/2025-11-19/14.log).
"""

from __future__ import annotations

import logging
import os
import threading
from datetime import datetime, timedelta
from typing import Optional

from app.core.config import settings


class HourlyFileHandler(logging.Handler):
    """A logging handler that writes to files organized by day/hour.

    Each emitted record is written to a file at: {log_dir}/{YYYY-MM-DD}/{HH}.log
    The handler will reopen the file when the hour changes.
    """

    def __init__(
        self, log_dir: str, level: int = logging.INFO, encoding: str = "utf-8"
    ):
        super().__init__(level)
        self.log_dir = log_dir
        self.encoding = encoding
        self._lock = threading.RLock()
        self._file = None
        self._current_hour = None
        self._open_file_for_current_hour()

    def _hour_path(self, when: Optional[datetime] = None) -> str:
        dt = when or datetime.now()
        day = dt.strftime("%Y-%m-%d")
        hour = dt.strftime("%H")
        folder = os.path.join(self.log_dir, day)
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, f"{hour}.log")

    def _open_file_for_current_hour(self) -> None:
        with self._lock:
            path = self._hour_path()
            self._current_hour = datetime.now().replace(
                minute=0, second=0, microsecond=0
            )
            # close existing
            if self._file:
                try:
                    self._file.close()
                except Exception:
                    pass
            # open new file in append mode
            self._file = open(path, "a", encoding=self.encoding)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            with self._lock:
                now = datetime.now().replace(minute=0, second=0, microsecond=0)
                if self._current_hour is None or now != self._current_hour:
                    # hour changed; reopen
                    self._open_file_for_current_hour()
                msg = self.format(record)
                self._file.write(msg + "\n")
                self._file.flush()
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        try:
            if self._file:
                try:
                    self._file.close()
                except Exception:
                    pass
                self._file = None
        finally:
            super().close()


def _cleanup_old_logs(log_dir: str, retention_days: int) -> None:
    """Remove day-folders older than retention_days."""
    try:
        cutoff = datetime.now() - timedelta(days=retention_days)
        if not os.path.isdir(log_dir):
            return
        for name in os.listdir(log_dir):
            path = os.path.join(log_dir, name)
            if not os.path.isdir(path):
                continue
            try:
                # folder name expected YYYY-MM-DD
                folder_dt = datetime.strptime(name, "%Y-%m-%d")
            except Exception:
                # skip non-conforming folders
                continue
            if folder_dt < cutoff:
                # remove folder and contents
                try:
                    for root, dirs, files in os.walk(path, topdown=False):
                        for f in files:
                            try:
                                os.remove(os.path.join(root, f))
                            except Exception:
                                pass
                        for d in dirs:
                            try:
                                os.rmdir(os.path.join(root, d))
                            except Exception:
                                pass
                    os.rmdir(path)
                except Exception:
                    pass
    except Exception:
        # never let cleanup crash the app
        return


def setup_logging() -> None:
    """Configure root logging from environment variables.

    Call this at application startup (before other modules configure loggers).
    """
    # Read configuration from centralized settings (pydantic BaseSettings)
    root_level_name = settings.log_level or "INFO"
    root_level = getattr(logging, root_level_name.upper(), logging.INFO)

    console_enabled = bool(settings.log_console)
    console_level_name = settings.log_console_level or root_level_name
    console_level = getattr(logging, console_level_name.upper(), root_level)

    file_enabled = bool(settings.log_file)
    file_level_name = settings.log_file_level or root_level_name
    file_level = getattr(logging, file_level_name.upper(), root_level)

    log_dir = settings.log_dir or "logs"
    retention_days = int(settings.log_retention_days or 7)

    # Basic root configuration
    logging.root.handlers = []
    logging.root.setLevel(root_level)

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    if console_enabled:
        ch = logging.StreamHandler()
        ch.setLevel(console_level)
        ch.setFormatter(formatter)
        logging.root.addHandler(ch)

    if file_enabled:
        # Ensure base log dir exists
        os.makedirs(log_dir, exist_ok=True)
        fh = HourlyFileHandler(log_dir=log_dir, level=file_level)
        fh.setLevel(file_level)
        fh.setFormatter(formatter)
        logging.root.addHandler(fh)

        # cleanup old logs asynchronously (fire-and-forget)
        try:
            t = threading.Thread(
                target=_cleanup_old_logs, args=(log_dir, retention_days), daemon=True
            )
            t.start()
        except Exception:
            pass

    # Reduce overly verbose third-party loggers by default
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("alembic").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("qdrant").setLevel(logging.WARNING)
    logging.getLogger("qdrant_client").setLevel(logging.WARNING)
    logging.getLogger("jieba").setLevel(logging.WARNING)
    logging.getLogger("rank_bm25").setLevel(logging.WARNING)

    # Try to silently initialize jieba to avoid noisy stdout/stderr messages
    try:
        import importlib
        import contextlib

        spec = importlib.util.find_spec("jieba")
        if spec is not None:
            with open(os.devnull, "w") as _devnull:
                try:
                    with (
                        contextlib.redirect_stdout(_devnull),
                        contextlib.redirect_stderr(_devnull),
                    ):
                        jieba = importlib.import_module("jieba")
                        # call initialize() if available to ensure dictionaries are loaded
                        try:
                            if hasattr(jieba, "initialize"):
                                jieba.initialize()
                        except Exception:
                            pass
                except Exception:
                    pass
    except Exception:
        pass


__all__ = ["setup_logging", "HourlyFileHandler"]
