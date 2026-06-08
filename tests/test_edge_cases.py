from __future__ import annotations

import os
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from vector_studio.models import TraceOptions, TraceResult
from vector_studio.tracer import trace_image


class TestEmptyAndCorruptFiles:
    def test_empty_file_raises_error(self, tmp_path: Path):
        empty = tmp_path / "empty.png"
        empty.write_bytes(b"")
        out = tmp_path / "out.svg"
        with pytest.raises((FileNotFoundError, ValueError, RuntimeError, OSError)):
            trace_image(empty, out)

    def test_corrupt_image_raises_error(self, tmp_path: Path, sample_image_corrupt: Path):
        out = tmp_path / "out.svg"
        with pytest.raises((ValueError, RuntimeError, OSError)):
            trace_image(sample_image_corrupt, out)

    def test_unsupported_extension(self, tmp_path: Path):
        bad = tmp_path / "image.gif"
        bad.write_text("not a real gif")
        out = tmp_path / "out.svg"
        with pytest.raises(ValueError, match="Unsupported input format"):
            trace_image(bad, out)

    def test_missing_input_file(self, tmp_path: Path):
        missing = tmp_path / "missing.png"
        out = tmp_path / "out.svg"
        with pytest.raises(FileNotFoundError, match="Input file not found"):
            trace_image(missing, out)


class TestPermissionAndDiskErrors:
    def test_unwritable_output_directory(self, tmp_path: Path, sample_image: Path, monkeypatch):
        out_dir = tmp_path / "readonly"
        out_dir.mkdir()
        # Windows doesn't support mode easily; mock mkdir to raise PermissionError
        with patch("pathlib.Path.mkdir", side_effect=PermissionError("Access denied")):
            with pytest.raises(PermissionError):
                trace_image(sample_image, out_dir / "out.svg")

    def test_disk_full_simulation(self, tmp_path: Path, sample_image: Path):
        out = tmp_path / "out.svg"
        with patch("pathlib.Path.write_text", side_effect=OSError(28, "No space left on device")):
            with pytest.raises(OSError, match="No space left"):
                trace_image(sample_image, out)


class TestConcurrency:
    def test_concurrent_trace_calls(self, tmp_path: Path):
        results = []
        errors = []

        def worker(idx: int):
            img = tmp_path / f"img_{idx}.png"
            img.write_bytes(b"fake")
            out = tmp_path / f"out_{idx}.svg"
            try:
                result = trace_image(img, out)
                results.append(result)
            except Exception as exc:
                errors.append(exc)

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = tmp_path / "normalized.png"
            with patch("vector_studio.tracer._trace_with_python_binding"):
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.svg_stats", return_value={"paths": 3}):
                        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
                        for t in threads:
                            t.start()
                        for t in threads:
                            t.join()

        assert len(results) == 5
        assert not errors

    def test_concurrent_batch_cli(self, tmp_path: Path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        for i in range(4):
            (input_dir / f"img{i}.png").write_bytes(b"fake")

        mock_result = TraceResult(
            input_path=input_dir / "img0.png",
            svg_path=output_dir / "img0.svg",
            engine="python-vtracer",
            elapsed_seconds=0.5,
            stats={"paths": 3},
        )

        with patch("vector_studio.task_queue.trace_image", return_value=mock_result):
            from vector_studio.cli import app
            from typer.testing import CliRunner
            runner = CliRunner()
            result = runner.invoke(app, ["batch", str(input_dir), str(output_dir), "--workers", "2"])
        assert result.exit_code == 0


class TestLargeFileHandling:
    def test_large_image_streaming(self, tmp_path: Path):
        img = tmp_path / "huge.png"
        # Create a moderately large image
        image = Image.new("RGB", (6000, 6000), color=(0, 0, 0))
        image.save(img, format="PNG")
        out = tmp_path / "out.svg"
        out.write_text("<svg></svg>")

        with patch("vector_studio.performance.StreamingImageProcessor._should_stream", return_value=True):
            with patch("vector_studio.performance.StreamingImageProcessor.process_large_image", return_value=out):
                with patch("vector_studio.tracer.svg_stats", return_value={"paths": 3}):
                    with patch("vector_studio.tracer.optimize_svg_file"):
                        result = trace_image(img, out, stream=True)
        assert result.engine == "streaming-vtracer"

    def test_very_large_file_size(self, tmp_path: Path):
        img = tmp_path / "big.png"
        image = Image.new("RGB", (100, 100))
        image.save(img, format="PNG")
        # Simulate large file by mocking stat
        fake_stat = MagicMock()
        fake_stat.st_size = 50 * 1024 * 1024  # 50 MB
        with patch("pathlib.Path.stat", return_value=fake_stat):
            from vector_studio.performance import StreamingImageProcessor
            assert StreamingImageProcessor._should_stream(img)


class TestNetworkAndExternalFailures:
    def test_api_client_http_error(self, tmp_path: Path):
        from vector_studio.api_client import VectorStudioClient
        client = VectorStudioClient("http://localhost:9999")
        with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
            with pytest.raises(Exception):
                client.health()

    def test_market_network_failure(self, tmp_path: Path):
        from vector_studio.market import PresetMarket
        market = PresetMarket()
        with patch("urllib.request.urlopen", side_effect=Exception("No network")):
            presets = market.discover_presets()
        assert presets == []


class TestMemoryAndResourceLimits:
    def test_memory_check_fallback(self):
        from vector_studio.performance import PerformanceMonitor
        monitor = PerformanceMonitor(max_memory_mb=512)
        with patch.dict("sys.modules", {"psutil": None}):
            mem = monitor.check_memory()
        assert mem["used_mb"] == 0.0
        assert mem["limit_mb"] == 512.0

    def test_lazy_module_loader_unload(self):
        from vector_studio.performance import LazyModuleLoader
        loader = LazyModuleLoader()
        with patch("importlib.import_module") as mock_import:
            mock_mod = MagicMock()
            mock_import.return_value = mock_mod
            mod = loader.load("fake_module")
            assert mod is mock_mod
            assert loader.is_loaded("fake_module")
            loader.unload("fake_module")
            assert not loader.is_loaded("fake_module")


class TestEmptyAndCorruptFilesMore:
    def test_zero_byte_jpg_raises_error(self, tmp_path: Path):
        empty = tmp_path / "empty.jpg"
        empty.write_bytes(b"")
        out = tmp_path / "out.svg"
        with pytest.raises((FileNotFoundError, ValueError, RuntimeError, OSError)):
            trace_image(empty, out)

    def test_truncated_png_raises_error(self, tmp_path: Path):
        bad = tmp_path / "bad.png"
        bad.write_bytes(b"\x89PNG\r\n\x1a\n")
        out = tmp_path / "out.svg"
        with pytest.raises((ValueError, RuntimeError, OSError)):
            trace_image(bad, out)

    def test_unsupported_extension_tiff(self, tmp_path: Path):
        # tiff is actually supported, so test a truly unsupported one
        bad = tmp_path / "image.raw"
        bad.write_text("not a real raw")
        out = tmp_path / "out.svg"
        with pytest.raises(ValueError, match="Unsupported input format"):
            trace_image(bad, out)


class TestNetworkAndExternalFailuresMore:
    def test_api_client_timeout(self, tmp_path: Path):
        from vector_studio.api_client import VectorStudioClient
        client = VectorStudioClient("http://localhost:9999")
        with patch("urllib.request.urlopen", side_effect=Exception("Timeout")):
            with pytest.raises(Exception):
                client.health()

    def test_market_search_network_failure(self, tmp_path: Path):
        from vector_studio.market import PresetMarket
        market = PresetMarket()
        with patch("urllib.request.urlopen", side_effect=Exception("DNS error")):
            presets = market.search("logo")
        assert presets == []


class TestConcurrencyMore:
    def test_concurrent_plugin_preprocess(self, tmp_path: Path):
        from vector_studio.plugin_interface import Plugin
        from vector_studio.plugins import PluginManager
        from PIL import Image
        import threading

        class SlowPlugin(Plugin):
            name = "slow"
            lock = threading.Lock()
            count = 0

            def preprocess(self, image, options):
                with self.lock:
                    SlowPlugin.count += 1
                return image

        manager = PluginManager()
        manager.register_plugin(SlowPlugin)
        img = Image.new("RGB", (10, 10))
        errors = []

        def worker():
            try:
                manager.run_preprocess(img, {})
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert SlowPlugin.count == 10

    def test_concurrent_batch_with_same_output_dir(self, tmp_path: Path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        for i in range(3):
            (input_dir / f"img{i}.png").write_bytes(b"fake")

        mock_result = TraceResult(
            input_path=input_dir / "img0.png",
            svg_path=output_dir / "img0.svg",
            engine="python-vtracer",
            elapsed_seconds=0.5,
            stats={"paths": 3},
        )

        with patch("vector_studio.task_queue.trace_image", return_value=mock_result):
            from vector_studio.cli import app
            from typer.testing import CliRunner
            runner = CliRunner()
            result = runner.invoke(app, ["batch", str(input_dir), str(output_dir), "--workers", "2"])
        assert result.exit_code == 0


class TestMemoryAndResourceLimitsMore:
    def test_performance_monitor_estimate_large_image(self):
        from vector_studio.performance import PerformanceMonitor
        from vector_studio.models import TraceOptions
        monitor = PerformanceMonitor()
        opts = TraceOptions(colormode="color", mode="spline")
        estimated = monitor.estimate_conversion_time((8000, 8000), opts)
        assert estimated > 0
        assert isinstance(estimated, float)

    def test_lazy_module_loader_double_load(self):
        from vector_studio.performance import LazyModuleLoader
        loader = LazyModuleLoader()
        with patch("importlib.import_module") as mock_import:
            mock_mod = MagicMock()
            mock_import.return_value = mock_mod
            loader.load("fake_module")
            loader.load("fake_module")
            assert mock_import.call_count == 1  # Should cache
