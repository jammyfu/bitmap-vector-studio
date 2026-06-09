from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vector_studio.health_check import (
    HealthChecker,
    HealthStatus,
    check_disk_space,
    check_memory,
    check_python_deps,
    check_vtracer,
)


class TestHealthChecker:
    def test_no_checks_returns_healthy(self):
        checker = HealthChecker()
        status = checker.check()
        assert status.status == "healthy"
        assert status.checks == {}
        assert status.version == "3.0.0"
        assert status.uptime_seconds >= 0

    def test_passing_checks_returns_healthy(self):
        checker = HealthChecker()
        checker.register("test1", lambda: {"foo": "bar"})
        checker.register("test2", lambda: 42)
        status = checker.check()
        assert status.status == "healthy"
        assert status.checks["test1"]["status"] == "pass"
        assert status.checks["test1"]["details"] == {"foo": "bar"}
        assert status.checks["test2"]["status"] == "pass"
        assert status.checks["test2"]["details"] == 42

    def test_failing_check_returns_degraded(self):
        checker = HealthChecker()
        checker.register("ok", lambda: "fine")
        checker.register("fail", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        status = checker.check()
        assert status.status == "degraded"
        assert status.checks["ok"]["status"] == "pass"
        assert status.checks["fail"]["status"] == "fail"
        assert "boom" in status.checks["fail"]["error"]

    def test_multiple_failing_checks_returns_unhealthy(self):
        checker = HealthChecker()
        checker.register("a", lambda: (_ for _ in ()).throw(RuntimeError("a")))
        checker.register("b", lambda: (_ for _ in ()).throw(RuntimeError("b")))
        status = checker.check()
        assert status.status == "unhealthy"

    def test_health_status_to_dict(self):
        status = HealthStatus(
            status="healthy",
            timestamp="2024-01-01T00:00:00",
            version="1.0.0",
            uptime_seconds=5.0,
            checks={},
        )
        d = status.to_dict()
        assert d["status"] == "healthy"
        assert d["version"] == "1.0.0"
        assert d["uptime_seconds"] == 5.0

    def test_version_fallback_on_import_error(self):
        checker = HealthChecker()
        with patch.dict("sys.modules", {"vector_studio": None}):
            version = checker._get_version()
        assert version == "unknown"


class TestCheckDiskSpace:
    def test_returns_free_and_total_gb(self):
        result = check_disk_space(path=Path.home(), min_gb=0.001)
        assert "free_gb" in result
        assert "total_gb" in result
        assert result["free_gb"] > 0
        assert result["total_gb"] > 0

    def test_raises_when_space_too_low(self):
        with patch("shutil.disk_usage") as mock_disk_usage:
            mock_usage = MagicMock()
            mock_usage.free = 100 * 1024 * 1024  # 100 MB
            mock_usage.total = 1024 * 1024 * 1024 * 1024
            mock_disk_usage.return_value = mock_usage
            with pytest.raises(RuntimeError, match="磁盘空间不足"):
                check_disk_space(path=Path.home(), min_gb=999999)


class TestCheckMemory:
    def test_returns_available_mb_when_psutil_present(self):
        result = check_memory(min_mb=1.0)
        assert "available_mb" in result
        # If psutil is installed, available_mb is a float; otherwise it's "unknown"
        if result["available_mb"] != "unknown":
            assert result["available_mb"] > 0
            assert "total_mb" in result

    def test_returns_unknown_when_psutil_missing(self):
        with patch.dict("sys.modules", {"psutil": None}):
            result = check_memory(min_mb=1.0)
        assert result["available_mb"] == "unknown"
        assert result["note"] == "psutil not installed"

    def test_raises_when_memory_too_low(self):
        pytest.importorskip("psutil")
        with patch("psutil.virtual_memory") as mock_vm:
            mock_mem = MagicMock()
            mock_mem.available = 50 * 1024 * 1024  # 50 MB
            mock_mem.total = 1024 * 1024 * 1024
            mock_vm.return_value = mock_mem
            with pytest.raises(RuntimeError, match="内存不足"):
                check_memory(min_mb=100.0)


class TestCheckPythonDeps:
    def test_returns_dependency_statuses(self):
        result = check_python_deps()
        assert isinstance(result, dict)
        for pkg in ["vtracer", "Pillow", "typer", "rich"]:
            assert pkg in result
            assert result[pkg] in ("ok", "missing")


class TestCheckVtracer:
    def test_returns_version_info(self):
        pytest.importorskip("vtracer")
        result = check_vtracer()
        assert "version" in result
