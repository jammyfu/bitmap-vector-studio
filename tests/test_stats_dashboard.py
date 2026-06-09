from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from vector_studio.stats_dashboard import StatsDashboard


class TestStatsDashboard:
    def test_empty_history_returns_empty_summary(self, tmp_path: Path):
        """无历史数据时返回空汇总."""
        dashboard = StatsDashboard(history_dir=tmp_path)
        summary = dashboard.get_summary(days=30)
        assert summary["total_conversions"] == 0
        assert summary["successful"] == 0
        assert summary["failed"] == 0
        assert summary["success_rate"] == 0
        assert summary["top_presets"] == []
        assert summary["average_duration"] == 0

    def test_get_summary_with_valid_entries(self, tmp_path: Path):
        """有有效历史记录时返回正确汇总."""
        history_file = tmp_path / "history.jsonl"
        now = datetime.now(timezone.utc)
        records = [
            {
                "timestamp": now.isoformat(),
                "preset_name": "logo",
                "elapsed_seconds": 1.5,
            },
            {
                "timestamp": (now - timedelta(days=1)).isoformat(),
                "preset_name": "poster",
                "elapsed_seconds": 2.0,
            },
            {
                "timestamp": (now - timedelta(days=5)).isoformat(),
                "preset_name": "logo",
                "elapsed_seconds": 1.0,
            },
        ]
        history_file.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in records),
            encoding="utf-8",
        )

        dashboard = StatsDashboard(history_dir=tmp_path)
        summary = dashboard.get_summary(days=30)
        assert summary["total_conversions"] == 3
        assert summary["successful"] == 3
        assert summary["failed"] == 0
        assert summary["success_rate"] == 100.0
        assert summary["average_duration"] == pytest.approx(1.5, 0.01)
        assert summary["top_presets"] == [("logo", 2), ("poster", 1)]

    def test_get_summary_ignores_outdated_entries(self, tmp_path: Path):
        """超出时间范围的记录被忽略."""
        history_file = tmp_path / "history.jsonl"
        now = datetime.now(timezone.utc)
        records = [
            {
                "timestamp": now.isoformat(),
                "preset_name": "logo",
                "elapsed_seconds": 1.0,
            },
            {
                "timestamp": (now - timedelta(days=40)).isoformat(),
                "preset_name": "old",
                "elapsed_seconds": 99.0,
            },
        ]
        history_file.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in records),
            encoding="utf-8",
        )

        dashboard = StatsDashboard(history_dir=tmp_path)
        summary = dashboard.get_summary(days=30)
        assert summary["total_conversions"] == 1
        assert summary["average_duration"] == pytest.approx(1.0, 0.01)

    def test_get_daily_trend_empty_history(self, tmp_path: Path):
        """无历史数据时每日趋势返回零计数."""
        dashboard = StatsDashboard(history_dir=tmp_path)
        trend = dashboard.get_daily_trend(days=7)
        assert len(trend) == 7
        for day in trend:
            assert "date" in day
            assert "count" in day
            assert day["count"] == 0

    def test_get_daily_trend_with_entries(self, tmp_path: Path):
        """有历史记录时每日趋势正确计数."""
        history_file = tmp_path / "history.jsonl"
        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")
        yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        records = [
            {"timestamp": now.isoformat(), "preset_name": "logo"},
            {"timestamp": now.isoformat(), "preset_name": "poster"},
            {"timestamp": (now - timedelta(days=1)).isoformat(), "preset_name": "logo"},
            {"timestamp": (now - timedelta(days=10)).isoformat(), "preset_name": "old"},
        ]
        history_file.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in records),
            encoding="utf-8",
        )

        dashboard = StatsDashboard(history_dir=tmp_path)
        trend = dashboard.get_daily_trend(days=7)
        assert len(trend) == 7
        today_entry = next(d for d in trend if d["date"] == today_str)
        yesterday_entry = next(d for d in trend if d["date"] == yesterday_str)
        assert today_entry["count"] == 2
        assert yesterday_entry["count"] == 1
