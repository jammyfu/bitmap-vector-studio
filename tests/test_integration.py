from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vector_studio.models import TraceOptions, TraceResult
from vector_studio.tracer import trace_image


class TestEndToEndConversion:
    def test_full_pipeline_mocked(self, tmp_path: Path, sample_image: Path):
        out = tmp_path / "result.svg"
        opts = TraceOptions(colormode="color", filter_speckle=2)
        normalized = tmp_path / "normalized.png"
        from PIL import Image
        Image.new("RGB", (10, 10)).save(normalized)

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = normalized
            with patch("vector_studio.tracer._trace_with_python_binding"):
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.svg_stats", return_value={"paths": 3}):
                        result = trace_image(sample_image, out, opts, optimize=True, name_layers=True, export_pdf=True, export_png=True, export_eps=True)

        assert result.input_path == sample_image
        assert result.svg_path == out
        assert result.engine == "python-vtracer"
        assert result.pdf_path is not None
        assert result.png_path is not None
        assert result.eps_path is not None

    def test_pipeline_with_plugins(self, tmp_path: Path, sample_image: Path):
        out = tmp_path / "result.svg"
        from vector_studio.plugin_interface import Plugin

        class DummyPlugin(Plugin):
            name = "dummy"

            def preprocess(self, image, options):
                return image

            def postprocess(self, svg_path, options):
                return svg_path

        normalized = tmp_path / "normalized.png"
        from PIL import Image
        Image.new("RGB", (10, 10)).save(normalized)

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = normalized
            with patch("vector_studio.tracer._trace_with_python_binding"):
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.svg_stats", return_value={"paths": 3}):
                        result = trace_image(sample_image, out, plugins=[DummyPlugin()], optimize=True)
        assert result.svg_path == out

    def test_pipeline_with_ai_simplify(self, tmp_path: Path, sample_image: Path):
        out = tmp_path / "result.svg"
        normalized = tmp_path / "normalized.png"
        from PIL import Image
        Image.new("RGB", (10, 10)).save(normalized)

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = normalized
            with patch("vector_studio.tracer._trace_with_python_binding"):
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.svg_stats", return_value={"paths": 3}):
                        with patch("vector_studio.ai_simplify.adaptive_simplify") as mock_simplify:
                            mock_simplify.return_value = MagicMock()
                            result = trace_image(sample_image, out, ai_simplify=True, simplify_type="photo")
        assert result.svg_path == out

    def test_pipeline_with_ai_ocr(self, tmp_path: Path, sample_image: Path):
        out = tmp_path / "result.svg"
        normalized = tmp_path / "normalized.png"
        from PIL import Image
        Image.new("RGB", (10, 10)).save(normalized)

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = normalized
            with patch("vector_studio.tracer._trace_with_python_binding"):
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.svg_stats", return_value={"paths": 3}):
                        with patch("vector_studio.ai_ocr.recognize_text_multilang", return_value=[{"text": "hello", "bbox": [0, 0, 10, 10]}]):
                            with patch("vector_studio.ai_ocr.integrate_text_to_svg"):
                                result = trace_image(sample_image, out, ai_ocr=True, ocr_lang="eng")
        assert result.svg_path == out

    def test_pipeline_preview_mode(self, tmp_path: Path, sample_image: Path):
        out = tmp_path / "result.svg"
        normalized = tmp_path / "normalized.png"
        from PIL import Image
        Image.new("RGB", (10, 10)).save(normalized)

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = normalized
            with patch("vector_studio.tracer._trace_with_python_binding"):
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.svg_stats", return_value={"paths": 3}):
                        result = trace_image(sample_image, out, preview_mode=True)
        assert result.svg_path == out
        assert result.pdf_path is None
        assert result.png_path is None

    def test_pipeline_streaming_mode(self, tmp_path: Path, sample_image_large: Path):
        out = tmp_path / "result.svg"
        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = tmp_path / "normalized.png"
            with patch("vector_studio.tracer.svg_stats", return_value={"paths": 3}):
                with patch("vector_studio.performance.StreamingImageProcessor._should_stream", return_value=True):
                    with patch("vector_studio.performance.StreamingImageProcessor.process_large_image", return_value=out):
                        result = trace_image(sample_image_large, out, stream=True)
        assert result.engine == "streaming-vtracer"

    def test_pipeline_gpu_flag(self, tmp_path: Path, sample_image: Path):
        out = tmp_path / "result.svg"
        normalized = tmp_path / "normalized.png"
        from PIL import Image
        Image.new("RGB", (10, 10)).save(normalized)

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = normalized
            with patch("vector_studio.tracer._trace_with_python_binding"):
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.svg_stats", return_value={"paths": 3}):
                        with patch("vector_studio.gpu_backend.detect_gpu", return_value=MagicMock(value="cuda")):
                            with patch("vector_studio.gpu_backend.gpu_preprocess") as mock_gpu:
                                mock_gpu.return_value = MagicMock()
                                result = trace_image(sample_image, out, use_gpu=True)
        assert result.svg_path == out


class TestBatchConversion:
    def test_batch_convert_multiple(self, tmp_path: Path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        for i in range(3):
            img = input_dir / f"img{i}.png"
            img.write_bytes(b"fake")

        mock_result = TraceResult(
            input_path=input_dir / "img0.png",
            svg_path=output_dir / "img0.svg",
            engine="python-vtracer",
            elapsed_seconds=0.5,
            stats={"paths": 3},
        )

        with patch("vector_studio.cli.trace_image", return_value=mock_result):
            from vector_studio.cli import app
            from typer.testing import CliRunner
            runner = CliRunner()
            result = runner.invoke(app, ["batch", str(input_dir), str(output_dir)])
        assert result.exit_code == 0
        assert "ok" in result.output

    def test_batch_with_plugins(self, tmp_path: Path):
        input_dir = tmp_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        (input_dir / "img.png").write_bytes(b"fake")

        mock_result = TraceResult(
            input_path=input_dir / "img.png",
            svg_path=output_dir / "img.svg",
            engine="python-vtracer",
            elapsed_seconds=0.5,
            stats={},
        )

        with patch("vector_studio.cli.trace_image", return_value=mock_result) as mock_trace:
            from vector_studio.cli import app
            from typer.testing import CliRunner
            runner = CliRunner()
            result = runner.invoke(app, ["batch", str(input_dir), str(output_dir), "--plugin", "watermark"])
        assert result.exit_code == 0
        mock_trace.assert_called_once()


class TestPluginIntegration:
    def test_plugin_preprocess_postprocess_hooks(self, tmp_path: Path):
        from vector_studio.plugin_interface import Plugin
        from vector_studio.plugins import PluginManager
        from PIL import Image

        class CounterPlugin(Plugin):
            name = "counter"
            calls: list[str] = []

            def preprocess(self, image, options):
                self.calls.append("preprocess")
                return image

            def postprocess(self, svg_path, options):
                self.calls.append("postprocess")
                return svg_path

            def on_convert_complete(self, result, options):
                self.calls.append("complete")

        manager = PluginManager()
        manager.register_plugin(CounterPlugin)
        img = Image.new("RGB", (10, 10))
        manager.run_preprocess(img, {})
        svg = tmp_path / "test.svg"
        svg.write_text("<svg></svg>")
        manager.run_postprocess(svg, {})
        manager.run_on_complete(MagicMock(), {})
        assert "preprocess" in CounterPlugin.calls
        assert "postprocess" in CounterPlugin.calls
        assert "complete" in CounterPlugin.calls


class TestConfigLoading:
    def test_config_loaded_in_trace_command(self, tmp_path: Path):
        from vector_studio.config import Config
        cfg = Config(default_preset="logo", export_pdf=True)
        config_path = tmp_path / "config.json"
        cfg.save(config_path)

        img = tmp_path / "img.png"
        img.write_bytes(b"fake")
        mock_result = TraceResult(
            input_path=img,
            svg_path=img.with_suffix(".svg"),
            engine="python-vtracer",
            elapsed_seconds=0.5,
            stats={},
            pdf_path=img.with_suffix(".pdf"),
        )

        with patch("vector_studio.cli.trace_image", return_value=mock_result) as mock_trace:
            from vector_studio.cli import app
            from typer.testing import CliRunner
            runner = CliRunner()
            result = runner.invoke(app, ["trace", str(img), "--config", str(config_path)])
        assert result.exit_code == 0
        passed_opts = mock_trace.call_args[0][2]
        assert passed_opts.colormode == "binary"  # logo preset
