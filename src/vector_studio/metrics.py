"""性能指标收集器.

收集转换耗时、成功率、队列长度等关键指标.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConversionMetrics:
    """转换指标."""

    total: int = 0
    successful: int = 0
    failed: int = 0
    total_duration: float = 0.0
    durations: deque[float] = field(default_factory=lambda: deque(maxlen=100))

    @property
    def success_rate(self) -> float:
        return self.successful / self.total * 100 if self.total > 0 else 0

    @property
    def average_duration(self) -> float:
        return self.total_duration / self.total if self.total > 0 else 0

    @property
    def p95_duration(self) -> float:
        if not self.durations:
            return 0.0
        sorted_d = sorted(self.durations)
        idx = int(len(sorted_d) * 0.95)
        return sorted_d[min(idx, len(sorted_d) - 1)]

    def record(self, duration: float, success: bool) -> None:
        self.total += 1
        self.total_duration += duration
        self.durations.append(duration)
        if success:
            self.successful += 1
        else:
            self.failed += 1


class MetricsCollector:
    """指标收集器."""

    def __init__(self) -> None:
        self.conversion = ConversionMetrics()
        self.queue_length = 0
        self.active_workers = 0
        self._lock = threading.Lock()

    def record_conversion(self, duration: float, success: bool) -> None:
        with self._lock:
            self.conversion.record(duration, success)

    def set_queue_length(self, length: int) -> None:
        with self._lock:
            self.queue_length = length

    def set_active_workers(self, count: int) -> None:
        with self._lock:
            self.active_workers = count

    def get_snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "conversion": {
                    "total": self.conversion.total,
                    "successful": self.conversion.successful,
                    "failed": self.conversion.failed,
                    "success_rate": round(self.conversion.success_rate, 2),
                    "average_duration": round(self.conversion.average_duration, 3),
                    "p95_duration": round(self.conversion.p95_duration, 3),
                },
                "queue": {
                    "length": self.queue_length,
                },
                "workers": {
                    "active": self.active_workers,
                },
            }


# 全局实例
_metrics = MetricsCollector()


def get_metrics() -> MetricsCollector:
    return _metrics
