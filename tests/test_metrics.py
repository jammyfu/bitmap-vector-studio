from __future__ import annotations

import threading
import time
from unittest.mock import patch

import pytest

from vector_studio.metrics import ConversionMetrics, MetricsCollector, get_metrics


class TestConversionMetrics:
    def test_success_rate_zero_when_empty(self):
        m = ConversionMetrics()
        assert m.success_rate == 0

    def test_success_rate_calculation(self):
        m = ConversionMetrics()
        m.record(1.0, True)
        m.record(2.0, False)
        m.record(3.0, True)
        assert m.success_rate == (2 / 3) * 100

    def test_average_duration(self):
        m = ConversionMetrics()
        m.record(1.0, True)
        m.record(3.0, True)
        assert m.average_duration == 2.0

    def test_p95_duration(self):
        m = ConversionMetrics()
        for i in range(1, 101):
            m.record(float(i), True)
        # 95th percentile: idx = int(100 * 0.95) = 95, sorted_d[95] = 96.0
        assert m.p95_duration == 96.0

    def test_p95_duration_empty(self):
        m = ConversionMetrics()
        assert m.p95_duration == 0.0

    def test_durations_ring_buffer_maxlen(self):
        m = ConversionMetrics()
        for i in range(150):
            m.record(float(i), True)
        assert len(m.durations) == 100


class TestMetricsCollector:
    def test_record_conversion(self):
        collector = MetricsCollector()
        collector.record_conversion(1.5, True)
        snapshot = collector.get_snapshot()
        assert snapshot["conversion"]["total"] == 1
        assert snapshot["conversion"]["successful"] == 1
        assert snapshot["conversion"]["failed"] == 0

    def test_set_queue_length_and_workers(self):
        collector = MetricsCollector()
        collector.set_queue_length(5)
        collector.set_active_workers(3)
        snapshot = collector.get_snapshot()
        assert snapshot["queue"]["length"] == 5
        assert snapshot["workers"]["active"] == 3

    def test_thread_safety(self):
        collector = MetricsCollector()
        errors = []

        def worker():
            try:
                for _ in range(100):
                    collector.record_conversion(0.1, True)
                    collector.set_queue_length(1)
                    collector.set_active_workers(1)
                    collector.get_snapshot()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        snapshot = collector.get_snapshot()
        assert snapshot["conversion"]["total"] == 400

    def test_get_metrics_singleton(self):
        m1 = get_metrics()
        m2 = get_metrics()
        assert m1 is m2
        m1.record_conversion(0.5, True)
        assert m2.get_snapshot()["conversion"]["total"] == 1
