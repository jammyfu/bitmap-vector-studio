from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vector_studio.models import TraceResult


class TestPerformanceBenchmark:
    def test_benchmark_command_runs(self, tmp_path: Path):
        from PIL import Image
        from vector_studio.cli import app
        from typer.testing import CliRunner

        img = tmp_path / "img.png"
        Image.new("RGB", (100, 100)).save(img)
        mock_result = TraceResult(
            input_path=img,
            svg_path=img.with_suffix(".svg"),
            engine="python-vtracer",
            elapsed_seconds=0.5,
            stats={"paths": 3},
        )

        with patch("vector_studio.cli.trace_image", return_value=mock_result):
            runner = CliRunner()
            result = runner.invoke(app, ["benchmark", str(img), "--runs", "2"])
        assert result.exit_code == 0
        assert "Benchmark" in result.output
        assert "Min" in result.output
        assert "Mean" in result.output

    def test_benchmark_with_gpu_flag(self, tmp_path: Path):
        from PIL import Image
        from vector_studio.cli import app
        from typer.testing import CliRunner

        img = tmp_path / "img.png"
        Image.new("RGB", (100, 100)).save(img)
        mock_result = TraceResult(
            input_path=img,
            svg_path=img.with_suffix(".svg"),
            engine="python-vtracer",
            elapsed_seconds=0.3,
            stats={},
        )

        with patch("vector_studio.cli.trace_image", return_value=mock_result):
            runner = CliRunner()
            result = runner.invoke(app, ["benchmark", str(img), "--runs", "1", "--gpu"])
        assert result.exit_code == 0

    def test_benchmark_with_stream_flag(self, tmp_path: Path):
        from PIL import Image
        from vector_studio.cli import app
        from typer.testing import CliRunner

        img = tmp_path / "img.png"
        Image.new("RGB", (100, 100)).save(img)
        mock_result = TraceResult(
            input_path=img,
            svg_path=img.with_suffix(".svg"),
            engine="streaming-vtracer",
            elapsed_seconds=0.8,
            stats={},
        )

        with patch("vector_studio.cli.trace_image", return_value=mock_result):
            runner = CliRunner()
            result = runner.invoke(app, ["benchmark", str(img), "--runs", "1", "--stream"])
        assert result.exit_code == 0

    def test_performance_monitor_estimate(self):
        from vector_studio.performance import PerformanceMonitor
        from vector_studio.models import TraceOptions

        monitor = PerformanceMonitor()
        opts = TraceOptions(colormode="color", mode="spline", denoise=True)
        estimated = monitor.estimate_conversion_time((1000, 1000), opts)
        assert estimated > 0
        assert isinstance(estimated, float)

    def test_performance_monitor_suggestions(self, tmp_path: Path):
        from vector_studio.performance import PerformanceMonitor

        monitor = PerformanceMonitor()
        img = tmp_path / "img.png"
        from PIL import Image
        Image.new("RGB", (6000, 6000)).save(img)
        suggestions = monitor.suggest_optimization(img)
        assert isinstance(suggestions, list)
        assert any("large" in s.lower() for s in suggestions)

    def test_streaming_processor_should_stream(self, tmp_path: Path):
        from vector_studio.performance import StreamingImageProcessor

        img = tmp_path / "big.png"
        from PIL import Image
        Image.new("RGB", (100, 100)).save(img)
        fake_stat = MagicMock()
        fake_stat.st_size = 15 * 1024 * 1024  # 15 MB
        with patch("pathlib.Path.stat", return_value=fake_stat):
            assert StreamingImageProcessor._should_stream(img)

    def test_streaming_processor_small_image_no_stream(self, tmp_path: Path):
        from vector_studio.performance import StreamingImageProcessor

        img = tmp_path / "small.png"
        from PIL import Image
        Image.new("RGB", (100, 100)).save(img)
        assert not StreamingImageProcessor._should_stream(img)

    def test_lazy_module_loader_preload(self):
        from vector_studio.performance import LazyModuleLoader

        loader = LazyModuleLoader()
        with patch("importlib.import_module") as mock_import:
            mock_mod = MagicMock()
            mock_import.return_value = mock_mod
            loader.preload_core_modules()
            assert loader.is_loaded("PIL.Image")

    def test_conversion_time_under_threshold(self, tmp_path: Path):
        """Ensure mocked conversion completes within a reasonable time threshold."""
        from vector_studio.tracer import trace_image

        img = tmp_path / "img.png"
        img.write_bytes(b"fake")
        out = tmp_path / "out.svg"

        start = time.perf_counter()
        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = tmp_path / "normalized.png"
            with patch("vector_studio.tracer._trace_with_python_binding"):
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.svg_stats", return_value={"paths": 3}):
                        trace_image(img, out)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0  # Should be nearly instant when mocked


class TestGPUBackendMock:
    def test_detect_gpu_none_when_no_libs(self):
        from vector_studio.gpu_backend import detect_gpu, GPUBackend

        with patch.dict("sys.modules", {"cupy": None, "pycuda": None, "torch": None, "pyopencl": None, "metal": None}):
            backend = detect_gpu()
        assert backend == GPUBackend.NONE

    def test_gpu_available_false_when_none(self):
        from vector_studio.gpu_backend import gpu_available, GPUBackend

        with patch("vector_studio.gpu_backend.detect_gpu", return_value=GPUBackend.NONE):
            assert not gpu_available()

    def test_gpu_preprocess_fallback_cpu(self):
        from vector_studio.gpu_backend import gpu_preprocess, GPUBackend
        from PIL import Image

        img = Image.new("RGB", (10, 10))
        with patch("vector_studio.gpu_backend._cpu_preprocess") as mock_cpu:
            mock_cpu.return_value = img
            result = gpu_preprocess(img, backend=GPUBackend.NONE)
        mock_cpu.assert_called_once()
        assert result is img

    def test_cpu_preprocess_runs(self):
        from vector_studio.gpu_backend import _cpu_preprocess
        from PIL import Image

        img = Image.new("RGB", (10, 10), color=(128, 128, 128))
        result = _cpu_preprocess(img)
        assert isinstance(result, Image.Image)
        assert result.size == (10, 10)


class TestBenchmarkMore:
    def test_benchmark_with_preset(self, tmp_path: Path):
        from PIL import Image
        from vector_studio.cli import app
        from typer.testing import CliRunner

        img = tmp_path / "img.png"
        Image.new("RGB", (100, 100)).save(img)
        mock_result = TraceResult(
            input_path=img,
            svg_path=img.with_suffix(".svg"),
            engine="python-vtracer",
            elapsed_seconds=0.4,
            stats={"paths": 3},
        )

        with patch("vector_studio.cli.trace_image", return_value=mock_result):
            runner = CliRunner()
            result = runner.invoke(app, ["benchmark", str(img), "--runs", "2", "--preset", "logo"])
        assert result.exit_code == 0
        assert "Benchmark" in result.output

    def test_benchmark_comparison_output(self, tmp_path: Path):
        from PIL import Image
        from vector_studio.cli import app
        from typer.testing import CliRunner

        img = tmp_path / "img.png"
        Image.new("RGB", (100, 100)).save(img)
        mock_result = TraceResult(
            input_path=img,
            svg_path=img.with_suffix(".svg"),
            engine="python-vtracer",
            elapsed_seconds=0.5,
            stats={"paths": 3},
        )

        with patch("vector_studio.cli.trace_image", return_value=mock_result):
            runner = CliRunner()
            result = runner.invoke(app, ["benchmark", str(img), "--runs", "3"])
        assert result.exit_code == 0
        assert "Benchmark" in result.output
        assert "Min" in result.output
        assert "Max" in result.output
        assert "Mean" in result.output

    def test_benchmark_with_gpu_flag(self, tmp_path: Path):
        from PIL import Image
        from vector_studio.cli import app
        from typer.testing import CliRunner

        img = tmp_path / "img.png"
        Image.new("RGB", (100, 100)).save(img)
        mock_result = TraceResult(
            input_path=img,
            svg_path=img.with_suffix(".svg"),
            engine="python-vtracer",
            elapsed_seconds=0.2,
            stats={"paths": 3},
        )

        with patch("vector_studio.cli.trace_image", return_value=mock_result):
            runner = CliRunner()
            result = runner.invoke(app, ["benchmark", str(img), "--runs", "1", "--gpu"])
        assert result.exit_code == 0

    def test_performance_monitor_suggestions_small_image(self, tmp_path: Path):
        from vector_studio.performance import PerformanceMonitor
        from PIL import Image

        monitor = PerformanceMonitor()
        img = tmp_path / "img.png"
        Image.new("RGB", (100, 100)).save(img)
        suggestions = monitor.suggest_optimization(img)
        assert isinstance(suggestions, list)

    def test_streaming_processor_dimensions_threshold(self, tmp_path: Path):
        from vector_studio.performance import StreamingImageProcessor

        img = tmp_path / "big.png"
        from PIL import Image
        Image.new("RGB", (6000, 6000)).save(img)
        assert StreamingImageProcessor._should_stream(img)

    def test_streaming_processor_small_dimensions_no_stream(self, tmp_path: Path):
        from vector_studio.performance import StreamingImageProcessor

        img = tmp_path / "small.png"
        from PIL import Image
        Image.new("RGB", (100, 100)).save(img)
        assert not StreamingImageProcessor._should_stream(img)
