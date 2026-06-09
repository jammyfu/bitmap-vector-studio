"""Bitmap Vector Studio 健康检查系统.

提供系统状态监控、依赖检查、性能指标收集.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


@dataclass
class HealthStatus:
    """健康状态."""

    status: str  # 'healthy', 'degraded', 'unhealthy'
    timestamp: str
    version: str
    uptime_seconds: float
    checks: dict[str, dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class HealthChecker:
    """健康检查器."""

    def __init__(self) -> None:
        self.start_time = time.time()
        self._checks: dict[str, Callable[[], Any]] = {}

    def register(self, name: str, check_fn: Callable[[], Any]) -> None:
        """注册检查项."""
        self._checks[name] = check_fn

    def check(self) -> HealthStatus:
        """执行所有检查."""
        checks: dict[str, dict[str, Any]] = {}
        overall = "healthy"

        for name, fn in self._checks.items():
            try:
                result = fn()
                checks[name] = {
                    "status": "pass",
                    "details": result,
                }
            except Exception as e:
                checks[name] = {
                    "status": "fail",
                    "error": str(e),
                }
                overall = "degraded" if overall == "healthy" else "unhealthy"

        # 如果没有注册任何检查，默认健康
        if not checks:
            overall = "healthy"

        return HealthStatus(
            status=overall,
            timestamp=datetime.now().isoformat(),
            version=self._get_version(),
            uptime_seconds=time.time() - self.start_time,
            checks=checks,
        )

    def _get_version(self) -> str:
        try:
            from vector_studio import __version__

            return __version__
        except Exception:
            return "unknown"


# 预定义检查项

def check_disk_space(path: Path = Path.home(), min_gb: float = 1.0) -> dict[str, Any]:
    """检查磁盘空间."""
    import shutil

    usage = shutil.disk_usage(path)
    free_gb = usage.free / (1024 ** 3)
    total_gb = usage.total / (1024 ** 3)
    if free_gb < min_gb:
        raise RuntimeError(f"磁盘空间不足: {free_gb:.1f}GB < {min_gb}GB")
    return {"free_gb": round(free_gb, 2), "total_gb": round(total_gb, 2)}


def check_memory(min_mb: float = 100.0) -> dict[str, Any]:
    """检查内存."""
    try:
        import psutil

        mem = psutil.virtual_memory()
        available_mb = mem.available / (1024 ** 2)
        if available_mb < min_mb:
            raise RuntimeError(f"内存不足: {available_mb:.1f}MB < {min_mb}MB")
        return {
            "available_mb": round(available_mb, 2),
            "total_mb": round(mem.total / (1024 ** 2), 2),
        }
    except ImportError:
        return {"available_mb": "unknown", "note": "psutil not installed"}


def check_python_deps() -> dict[str, Any]:
    """检查Python依赖."""
    deps: dict[str, str] = {}
    for pkg in ["vtracer", "Pillow", "typer", "rich"]:
        try:
            __import__(pkg)
            deps[pkg] = "ok"
        except ImportError:
            deps[pkg] = "missing"
    return deps


def check_vtracer() -> dict[str, Any]:
    """检查vtracer可用性."""
    import vtracer

    return {"version": getattr(vtracer, "__version__", "unknown")}
