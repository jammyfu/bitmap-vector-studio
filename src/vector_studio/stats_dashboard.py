"""统计仪表盘数据生成器.

生成转换统计、趋势分析、效率指标.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class StatsDashboard:
    """统计仪表盘."""

    def __init__(self, history_dir: Path | None = None):
        self.history_dir = history_dir or Path.home() / ".bitmap_vector_studio"

    def get_summary(self, days: int = 30) -> dict[str, Any]:
        """获取汇总统计."""
        # 读取历史数据
        history_file = self.history_dir / "history.jsonl"
        if not history_file.exists():
            return self._empty_summary()

        entries = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        for line in history_file.read_text(encoding="utf-8").strip().split("\n"):
            try:
                entry = json.loads(line)
                entry_time = datetime.fromisoformat(
                    entry.get("timestamp", "2000-01-01")
                )
                # Ensure both datetimes are timezone-aware for comparison
                if entry_time.tzinfo is None:
                    entry_time = entry_time.replace(tzinfo=timezone.utc)
                if entry_time > cutoff:
                    entries.append(entry)
            except Exception:
                continue

        if not entries:
            return self._empty_summary()

        total = len(entries)
        successful = total  # history only records successful conversions
        presets = Counter(e.get("preset_name", "unknown") for e in entries)

        return {
            "period_days": days,
            "total_conversions": total,
            "successful": successful,
            "failed": 0,
            "success_rate": 100.0 if total > 0 else 0,
            "top_presets": presets.most_common(5),
            "average_duration": sum(e.get("elapsed_seconds", 0) for e in entries) / total
            if total > 0
            else 0,
        }

    def _empty_summary(self) -> dict[str, Any]:
        return {
            "period_days": 0,
            "total_conversions": 0,
            "successful": 0,
            "failed": 0,
            "success_rate": 0,
            "top_presets": [],
            "average_duration": 0,
        }

    def get_daily_trend(self, days: int = 14) -> list[dict[str, Any]]:
        """获取每日趋势."""
        history_file = self.history_dir / "history.jsonl"
        counts: dict[str, int] = {}

        if history_file.exists():
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            for line in history_file.read_text(encoding="utf-8").strip().split("\n"):
                try:
                    entry = json.loads(line)
                    entry_time = datetime.fromisoformat(
                        entry.get("timestamp", "2000-01-01")
                    )
                    # Ensure both datetimes are timezone-aware for comparison
                    if entry_time.tzinfo is None:
                        entry_time = entry_time.replace(tzinfo=timezone.utc)
                    if entry_time > cutoff:
                        date_key = entry_time.strftime("%Y-%m-%d")
                        counts[date_key] = counts.get(date_key, 0) + 1
                except Exception:
                    continue

        # 返回最近14天每天的转换数量
        result = []
        for i in range(days - 1, -1, -1):
            date = datetime.now(timezone.utc) - timedelta(days=i)
            date_key = date.strftime("%Y-%m-%d")
            result.append({
                "date": date_key,
                "count": counts.get(date_key, 0),
            })
        return result
