from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from vector_studio.models import TraceOptions
from vector_studio.performance import (
    LazyModuleLoader,
    PerformanceMonitor,
    StreamingImageProcessor,
    _detect_gpu,
    _GPUBackend,
)


class TestPerformanceMonitor:
    def test_check_memory_returns_dict_with_keys(self):
        monitor = PerformanceMonitor(max_memory_mb=512)
        mem = monitor.check_memory()
        assert isinstance(mem, dict)
        assert "used_mb" in mem
        assert "available_mb" in mem
        assert "limit_mb" in mem
        assert "percent" in mem
        assert mem["limit_mb"] == 512.0

    def test_estimate_conversion_time_returns_positive_float(self):
        monitor = PerformanceMonitor()
        opts = TraceOptions(colormode="color", mode="spline", color_precision=6, max_iterations=10)
        estimated = monitor.estimate_conversion_time((1000, 1000), opts)
        assert isinstance(estimated, float)
        assert estimated > 0

    def test_estimate_conversion_time_scales_with_options(self):
        monitor = PerformanceMonitor()
        base_opts = TraceOptions(colormode="binary", mode="polygon", color_precision=1, max_iterations=1)
        high_opts = TraceOptions(colormode="color", mode="spline", color_precision=8, max_iterations=50)
        base_est = monitor.estimate_conversion_time((1000, 1000), base_opts)
        high_est = monitor.estimate_conversion_time((1000, 1000), high_opts)
        assert high_est > base_est

    def test_suggest_optimization_for_large_image(self, tmp_path: Path):
        monitor = PerformanceMonitor()
        img_path = tmp_path / "large.png"
        img = Image.new("RGB", (6000, 6000), color=(255, 0, 0))
        img.save(img_path, format="PNG")
        suggestions = monitor.suggest_optimization(img_path)
        assert isinstance(suggestions, list)
        assert any("large" in s.lower() or "downscale" in s.lower() for s in suggestions)

    def test_suggest_optimization_for_small_image(self, tmp_path: Path):
        monitor = PerformanceMonitor()
        img_path = tmp_path / "small.png"
        img = Image.new("RGB", (100, 100), color=(0, 255, 0))
        img.save(img_path, format="PNG")
        suggestions = monitor.suggest_optimization(img_path)
        assert isinstance(suggestions, list)
        # Small images may still get GPU-related suggestions
        assert all(isinstance(s, str) for s in suggestions)


class TestStreamingImageProcessor:
    def test_should_stream_true_for_large_file(self, tmp_path: Path):
        img_path = tmp_path / "big.png"
        img = Image.new("RGB", (100, 100), color=(0, 0, 255))
        img.save(img_path, format="PNG")
        # Artificially inflate file size to > 10 MB
        img_path.write_bytes(b"0" * 11 * 1024 * 1024)
        assert StreamingImageProcessor._should_stream(img_path) is True

    def test_should_stream_true_for_large_dimensions(self, tmp_path: Path):
        img_path = tmp_path / "bigdim.png"
        img = Image.new("RGB", (6000, 100), color=(0, 0, 255))
        img.save(img_path, format="PNG")
        assert StreamingImageProcessor._should_stream(img_path, (6000, 100)) is True

    def test_should_stream_false_for_small_file(self, tmp_path: Path):
        img_path = tmp_path / "small.png"
        img = Image.new("RGB", (100, 100), color=(0, 0, 255))
        img.save(img_path, format="PNG")
        assert StreamingImageProcessor._should_stream(img_path) is False

    def test_process_large_image_fallback_for_small_image(self, tmp_path: Path):
        img_path = tmp_path / "small.png"
        out_path = tmp_path / "out.svg"
        img = Image.new("RGB", (100, 100), color=(0, 0, 255))
        img.save(img_path, format="PNG")

        with patch("vector_studio.tracer.trace_image") as mock_trace:
            mock_trace.return_value = MagicMock(svg_path=out_path)
            processor = StreamingImageProcessor()
            result = processor.process_large_image(img_path, out_path, TraceOptions())
        assert result == out_path
        mock_trace.assert_called_once()


class TestLazyModuleLoader:
    def test_load_imports_on_first_call(self):
        loader = LazyModuleLoader()
        mod = loader.load("os")
        assert mod is not None
        assert loader.is_loaded("os")

    def test_unload_removes_module(self):
        loader = LazyModuleLoader()
        loader.load("os")
        assert loader.is_loaded("os")
        loader.unload("os")
        assert not loader.is_loaded("os")

    def test_preload_core_modules_loads_expected(self):
        loader = LazyModuleLoader()
        loader.preload_core_modules()
        assert loader.is_loaded("PIL.Image")
        assert loader.is_loaded("vector_studio.models")

    def test_preload_core_modules_marks_core(self):
        loader = LazyModuleLoader()
        loader.preload_core_modules()
        # Core modules should not be removed from sys.modules by unload
        import sys

        loader.unload("PIL.Image")
        assert "PIL.Image" in sys.modules
