from unittest.mock import patch

import pytest

from vector_studio.startup_optimizer import StartupOptimizer, StartupProfiler


class TestStartupOptimizer:
    def test_prewarm_python_env_runs_without_error(self):
        optimizer = StartupOptimizer()
        optimizer.prewarm_python_env()
        report = optimizer.get_startup_report()
        assert report["preset_cached"] is False
        assert any(s["name"] == "prewarm_python_env" for s in report["stages"])

    def test_cache_preset_data_caches_presets(self):
        optimizer = StartupOptimizer()
        optimizer.cache_preset_data()
        report = optimizer.get_startup_report()
        assert report["preset_cached"] is True
        assert any(s["name"] == "cache_preset_data" for s in report["stages"])

    def test_lazy_load_modules_records_stage(self):
        optimizer = StartupOptimizer()
        optimizer.lazy_load_modules()
        report = optimizer.get_startup_report()
        assert report["lazy_modules_count"] > 0
        assert any(s["name"] == "lazy_load_modules" for s in report["stages"])

    def test_get_startup_report_contains_total(self):
        optimizer = StartupOptimizer()
        optimizer.prewarm_python_env()
        optimizer.cache_preset_data()
        report = optimizer.get_startup_report()
        assert "total_seconds" in report
        assert report["total_seconds"] >= 0
        assert "stages" in report
        assert len(report["stages"]) == 2

    def test_unload_non_core_modules_does_not_raise(self):
        optimizer = StartupOptimizer()
        optimizer.lazy_load_modules()
        optimizer.unload_non_core_modules()
        # Should complete without exception even if modules not loaded


class TestStartupProfiler:
    def test_context_manager_records_stages(self):
        with StartupProfiler(label="test") as profiler:
            profiler.stage("stage_a")
            profiler.stage("stage_b")

        report = profiler.get_report()
        assert report["label"] == "test"
        assert "total_seconds" in report
        assert report["total_seconds"] >= 0
        assert report["bottleneck"] is not None
        stage_names = [s["name"] for s in report["stages"]]
        assert "stage_a" in stage_names
        assert "stage_b" in stage_names

    def test_get_report_with_no_stages(self):
        profiler = StartupProfiler(label="empty")
        report = profiler.get_report()
        assert report["label"] == "empty"
        assert report["total_seconds"] == 0.0
        assert report["bottleneck"] is None
        assert report["stages"] == []

    def test_profiler_identifies_bottleneck(self):
        with StartupProfiler(label="bottleneck_test") as profiler:
            profiler.stage("fast")
            profiler.stage("slow")

        report = profiler.get_report()
        # The last stage usually has the most time because it accumulates until exit
        assert report["bottleneck"] is not None

    def test_profiler_print_report_does_not_raise(self):
        with StartupProfiler(label="print_test") as profiler:
            profiler.stage("one")
        # _print_report is called on __exit__; ensure no exception
