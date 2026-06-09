"""审计日志系统.

记录所有关键操作，支持结构化日志输出.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class AuditLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SECURITY = "security"


class AuditEvent:
    """审计事件."""

    def __init__(self, level: AuditLevel, action: str, user: str, resource: str, details: dict[str, Any] | None = None):
        self.timestamp = datetime.now().isoformat()
        self.level = level.value
        self.action = action
        self.user = user
        self.resource = resource
        self.details = details or {}

    def to_dict(self) -> dict:
        return {
            'timestamp': self.timestamp,
            'level': self.level,
            'action': self.action,
            'user': self.user,
            'resource': self.resource,
            'details': self.details,
        }


class AuditLogger:
    """审计日志记录器."""

    def __init__(self, log_dir: Path | None = None, max_size_mb: int = 100):
        self.log_dir = log_dir or Path.home() / '.bitmap_vector_studio' / 'audit'
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_mb = max_size_mb
        self._lock = threading.Lock()
        self._current_file = self._get_log_file()

    def _get_log_file(self) -> Path:
        date = datetime.now().strftime('%Y-%m-%d')
        return self.log_dir / f"audit-{date}.jsonl"

    def log(self, level: AuditLevel, action: str, user: str, resource: str, details: dict[str, Any] | None = None) -> None:
        event = AuditEvent(level, action, user, resource, details)
        with self._lock:
            file = self._get_log_file()
            with open(file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + '\n')

    def info(self, action: str, user: str, resource: str, details: dict[str, Any] | None = None) -> None:
        self.log(AuditLevel.INFO, action, user, resource, details)

    def security(self, action: str, user: str, resource: str, details: dict[str, Any] | None = None) -> None:
        self.log(AuditLevel.SECURITY, action, user, resource, details)

    def query(self, start_time: str | None = None, end_time: str | None = None, user: str | None = None, action: str | None = None, limit: int = 100) -> list[dict]:
        """查询日志."""
        results = []
        for file in sorted(self.log_dir.glob('audit-*.jsonl'), reverse=True):
            with open(file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        event = json.loads(line)
                        if start_time and event['timestamp'] < start_time:
                            continue
                        if end_time and event['timestamp'] > end_time:
                            continue
                        if user and event['user'] != user:
                            continue
                        if action and event['action'] != action:
                            continue
                        results.append(event)
                        if len(results) >= limit:
                            return results
                    except json.JSONDecodeError:
                        continue
        return results
