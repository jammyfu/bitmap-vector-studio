from __future__ import annotations

import importlib
import logging
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class _StageRecord:
    name: str
    start: float
    end: float = 0.0

    @property
    def elapsed(self) -> float:
        return self.end - self.start


class StartupOptimizer:
    """Optimize application startup by prewarming imports and caching data."""

    def __init__(self) -> None:
        self._preset_cache: dict[str, Any] | None = None
        self._stages: list[_StageRecord] = []
        self._lazy_modules: set[str] = set()

    def prewarm_python_env(self) -> None:
        """Import commonly-used modules so they are ready in memory.

        This reduces latency on the first real conversion because Python
        modules are parsed and cached eagerly.
        """
        start = time.perf_counter()
        modules = [
            "PIL.Image",
            "PIL.ImageFilter",
            "PIL.ImageOps",
            "PIL.ImageDraw",
            "xml.etree.ElementTree",
            "pathlib",
            "tempfile",
            "json",
        ]
        for name in modules:
            try:
                importlib.import_module(name)
            except Exception as exc:
                logger.debug("Prewarm failed for %s: %s", name, exc)
        self._stages.append(_StageRecord("prewarm_python_env", start, time.perf_counter()))

    def cache_preset_data(self) -> None:
        """Load built-in presets into memory so they can be reused without disk I/O."""
        start = time.perf_counter()
        try:
            from .presets import PRESETS

            self._preset_cache = dict(PRESETS)
        except Exception as exc:
            logger.debug("Failed to cache presets: %s", exc)
        self._stages.append(_StageRecord("cache_preset_data", start, time.perf_counter()))

    def lazy_load_modules(self) -> None:
        """Mark heavy non-core modules for lazy loading.

        The actual unloading is deferred to the first call of
        :meth:`unload_non_core_modules`.
        """
        start = time.perf_counter()
        heavy_modules = [
            "vector_studio.ai_simplify",
            "vector_studio.ai_ocr",
            "vector_studio.enhance",
            "vector_studio.smart_recommend",
            "vector_studio.market",
        ]
        self._lazy_modules.update(heavy_modules)
        self._stages.append(_StageRecord("lazy_load_modules", start, time.perf_counter()))

    def unload_non_core_modules(self) -> None:
        """Remove heavy modules from ``sys.modules`` to free memory.

        They will be re-imported on next use (lazy loading).
        """
        for name in list(self._lazy_modules):
            if name in sys.modules:
                try:
                    del sys.modules[name]
                except Exception as exc:
                    logger.debug("Failed to unload %s: %s", name, exc)

    def get_startup_report(self) -> dict[str, Any]:
        """Return a structured report of startup timings and cache state.

        Returns
        -------
        dict
            Keys include ``stages``, ``total_seconds``, ``preset_cached``,
            ``lazy_modules_count``.
        """
        total = sum(s.elapsed for s in self._stages)
        return {
            "stages": [
                {"name": s.name, "elapsed_seconds": round(s.elapsed, 4)} for s in self._stages
            ],
            "total_seconds": round(total, 4),
            "preset_cached": self._preset_cache is not None,
            "lazy_modules_count": len(self._lazy_modules),
        }


class StartupProfiler:
    """Context manager that profiles startup stages and prints a bottleneck summary."""

    def __init__(self, label: str = "startup") -> None:
        self.label = label
        self._records: list[_StageRecord] = []
        self._current: _StageRecord | None = None

    def stage(self, name: str) -> "StartupProfiler":
        """Begin a named stage.  Call repeatedly to mark stage boundaries."""
        now = time.perf_counter()
        if self._current is not None:
            self._current.end = now
            self._records.append(self._current)
        self._current = _StageRecord(name, now)
        return self

    def __enter__(self) -> StartupProfiler:
        self.stage("begin")
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        now = time.perf_counter()
        if self._current is not None:
            self._current.end = now
            self._records.append(self._current)
        self._print_report()

    def _print_report(self) -> None:
        total = sum(r.elapsed for r in self._records)
        lines = [f"[{self.label}] Startup profile ({total:.3f}s total):"]
        if total > 0:
            for r in self._records:
                pct = r.elapsed / total * 100
                lines.append(f"  {r.name}: {r.elapsed:.3f}s ({pct:.1f}%)")
            # Identify bottleneck
            bottleneck = max(self._records, key=lambda r: r.elapsed)
            lines.append(f"  Bottleneck: {bottleneck.name} ({bottleneck.elapsed:.3f}s)")
        else:
            lines.append("  (no measurable time)")
        logger.info("\n".join(lines))

    def get_report(self) -> dict[str, Any]:
        """Return the profiling report as a dictionary."""
        total = sum(r.elapsed for r in self._records)
        return {
            "label": self.label,
            "total_seconds": round(total, 4),
            "stages": [
                {"name": r.name, "elapsed_seconds": round(r.elapsed, 4)} for r in self._records
            ],
            "bottleneck": (
                max(self._records, key=lambda r: r.elapsed).name if self._records else None
            ),
        }
