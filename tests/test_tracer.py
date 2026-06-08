from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vector_studio.models import TraceOptions, TraceResult
from vector_studio.tracer import trace_image, SUPPORTED_EXTENSIONS


class TestTraceImageInputValidation:
    def test_missing_input_raises_file_not_found(self, tmp_path):
        missing = tmp_path / "missing.png"
        out = tmp_path / "out.svg"
        with pytest.raises(FileNotFoundError, match="Input file not found"):
            trace_image(missing, out)

    def test_unsupported_format_raises_value_error(self, tmp_path):
        bad = tmp_path / "image.gif"
        bad.write_text("not a real gif", encoding="utf-8")
        out = tmp_path / "out.svg"
        with pytest.raises(ValueError, match="Unsupported input format"):
            trace_image(bad, out)

    @pytest.mark.parametrize("ext", [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"])
    def test_supported_extensions_accepted(self, ext, tmp_path):
        img = tmp_path / f"image{ext}"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"
        # Will fail later in the pipeline, but not on extension check
        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = tmp_path / "normalized.png"
            with patch("vector_studio.tracer._trace_with_python_binding") as mock_trace:
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.svg_stats", return_value={}):
                        trace_image(img, out)


class TestTraceImageOutputPath:
    def test_output_auto_corrected_to_svg(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.pdf"

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = tmp_path / "normalized.png"
            with patch("vector_studio.tracer._trace_with_python_binding") as mock_trace:
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.svg_stats", return_value={}):
                        result = trace_image(img, out)
        assert result.svg_path.suffix == ".svg"
        assert result.svg_path == tmp_path / "out.svg"

    def test_output_keeps_svg_suffix(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = tmp_path / "normalized.png"
            with patch("vector_studio.tracer._trace_with_python_binding") as mock_trace:
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.svg_stats", return_value={}):
                        result = trace_image(img, out)
        assert result.svg_path == out


class TestTraceImageEngineSelection:
    def test_python_binding_used_when_available(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = tmp_path / "normalized.png"
            with patch("vector_studio.tracer._trace_with_python_binding") as mock_py:
                with patch("vector_studio.tracer._trace_with_cli") as mock_cli:
                    with patch("vector_studio.tracer.optimize_svg_file"):
                        with patch("vector_studio.tracer.svg_stats", return_value={}):
                            result = trace_image(img, out)
        mock_py.assert_called_once()
        mock_cli.assert_not_called()
        assert result.engine == "python-vtracer"

    def test_cli_fallback_when_python_binding_fails(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = tmp_path / "normalized.png"
            with patch("vector_studio.tracer._trace_with_python_binding", side_effect=ImportError("no vtracer")) as mock_py:
                with patch("vector_studio.tracer._trace_with_cli") as mock_cli:
                    with patch("vector_studio.tracer.optimize_svg_file"):
                        with patch("vector_studio.tracer.svg_stats", return_value={}):
                            result = trace_image(img, out)
        mock_py.assert_called_once()
        mock_cli.assert_called_once()
        assert result.engine == "vtracer-cli"

    def test_raises_when_both_engines_fail(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = tmp_path / "normalized.png"
            with patch("vector_studio.tracer._trace_with_python_binding", side_effect=ImportError("no vtracer")):
                with patch("vector_studio.tracer._trace_with_cli", side_effect=RuntimeError("no cli")):
                    with pytest.raises(RuntimeError, match="VTracer conversion failed"):
                        trace_image(img, out)


class TestTraceImageOptionsPassing:
    def test_options_passed_to_prepare_and_trace(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"
        opts = TraceOptions(colormode="binary", filter_speckle=8)

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = tmp_path / "normalized.png"
            with patch("vector_studio.tracer._trace_with_python_binding") as mock_trace:
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.svg_stats", return_value={}):
                        trace_image(img, out, opts)

        mock_prepare.assert_called_once()
        assert mock_prepare.call_args[0][2] == opts
        mock_trace.assert_called_once()
        # The options should be validated before use
        assert mock_trace.call_args[0][2].colormode == "binary"

    def test_default_options_used_when_none_provided(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = tmp_path / "normalized.png"
            with patch("vector_studio.tracer._trace_with_python_binding") as mock_trace:
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.svg_stats", return_value={}):
                        trace_image(img, out)

        assert mock_trace.call_args[0][2].colormode == "color"


class TestTraceImagePostProcessing:
    def test_optimize_called_by_default(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = tmp_path / "normalized.png"
            with patch("vector_studio.tracer._trace_with_python_binding"):
                with patch("vector_studio.tracer.optimize_svg_file") as mock_opt:
                    with patch("vector_studio.tracer.svg_stats", return_value={}):
                        trace_image(img, out, optimize=True)
        mock_opt.assert_called_once_with(out)

    def test_optimize_skipped_when_false(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = tmp_path / "normalized.png"
            with patch("vector_studio.tracer._trace_with_python_binding"):
                with patch("vector_studio.tracer.optimize_svg_file") as mock_opt:
                    with patch("vector_studio.tracer.svg_stats", return_value={}):
                        trace_image(img, out, optimize=False)
        mock_opt.assert_not_called()

    def test_name_layers_called_when_true(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = tmp_path / "normalized.png"
            with patch("vector_studio.tracer._trace_with_python_binding"):
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.name_svg_layers") as mock_name:
                        with patch("vector_studio.tracer.svg_stats", return_value={}):
                            trace_image(img, out, name_layers=True)
        mock_name.assert_called_once_with(out)

    def test_name_layers_skipped_when_false(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = tmp_path / "normalized.png"
            with patch("vector_studio.tracer._trace_with_python_binding"):
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.name_svg_layers") as mock_name:
                        with patch("vector_studio.tracer.svg_stats", return_value={}):
                            trace_image(img, out, name_layers=False)
        mock_name.assert_not_called()

    def test_export_pdf_called_when_true(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = tmp_path / "normalized.png"
            with patch("vector_studio.tracer._trace_with_python_binding"):
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.export_svg_to_pdf", return_value=tmp_path / "out.pdf") as mock_pdf:
                        with patch("vector_studio.tracer.svg_stats", return_value={}):
                            result = trace_image(img, out, export_pdf=True)
        mock_pdf.assert_called_once()
        assert result.pdf_path == tmp_path / "out.pdf"

    def test_export_png_called_when_true(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = tmp_path / "normalized.png"
            with patch("vector_studio.tracer._trace_with_python_binding"):
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.export_svg_to_png", return_value=tmp_path / "out.png") as mock_png:
                        with patch("vector_studio.tracer.svg_stats", return_value={}):
                            result = trace_image(img, out, export_png=True, png_scale=2.0)
        mock_png.assert_called_once_with(out, out.with_suffix(".png"), scale=2.0)
        assert result.png_path == tmp_path / "out.png"

    def test_export_eps_called_when_true(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = tmp_path / "normalized.png"
            with patch("vector_studio.tracer._trace_with_python_binding"):
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.export_svg_to_eps_with_inkscape", return_value=tmp_path / "out.eps") as mock_eps:
                        with patch("vector_studio.tracer.svg_stats", return_value={}):
                            result = trace_image(img, out, export_eps=True)
        mock_eps.assert_called_once()
        assert result.eps_path == tmp_path / "out.eps"


class TestTraceImageResult:
    def test_result_contains_input_and_output_paths(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = tmp_path / "normalized.png"
            with patch("vector_studio.tracer._trace_with_python_binding"):
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.svg_stats", return_value={"paths": 3}):
                        result = trace_image(img, out)

        assert result.input_path == img
        assert result.svg_path == out
        assert result.stats == {"paths": 3}
        assert isinstance(result.elapsed_seconds, float)
        assert result.elapsed_seconds >= 0

    def test_result_engine_python_by_default(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = tmp_path / "normalized.png"
            with patch("vector_studio.tracer._trace_with_python_binding"):
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.svg_stats", return_value={}):
                        result = trace_image(img, out)
        assert result.engine == "python-vtracer"


class TestTraceWithPythonBinding:
    def test_calls_vtracer_convert(self, tmp_path):
        from vector_studio.tracer import _trace_with_python_binding
        opts = TraceOptions()
        fake_vtracer = MagicMock()
        with patch.dict("sys.modules", {"vtracer": fake_vtracer}):
            _trace_with_python_binding(tmp_path / "in.png", tmp_path / "out.svg", opts)
        fake_vtracer.convert_image_to_svg_py.assert_called_once_with(
            str(tmp_path / "in.png"),
            str(tmp_path / "out.svg"),
            **opts.vtracer_kwargs(),
        )

    def test_raises_runtime_error_when_vtracer_missing(self, tmp_path):
        from vector_studio.tracer import _trace_with_python_binding
        opts = TraceOptions()
        with patch.dict("sys.modules", {"vtracer": None}):
            with pytest.raises(RuntimeError, match="Python package 'vtracer' is not installed"):
                _trace_with_python_binding(tmp_path / "in.png", tmp_path / "out.svg", opts)


class TestTraceWithCli:
    def test_calls_subprocess_with_cli_args(self, tmp_path):
        from vector_studio.tracer import _trace_with_cli
        opts = TraceOptions()
        with patch("shutil.which", return_value="/usr/bin/vtracer"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
                _trace_with_cli(tmp_path / "in.png", tmp_path / "out.svg", opts)
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "/usr/bin/vtracer"

    def test_raises_when_executable_not_found(self, tmp_path):
        from vector_studio.tracer import _trace_with_cli
        opts = TraceOptions()
        with patch("shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="VTracer CLI was not found"):
                _trace_with_cli(tmp_path / "in.png", tmp_path / "out.svg", opts)

    def test_raises_on_nonzero_returncode(self, tmp_path):
        from vector_studio.tracer import _trace_with_cli
        opts = TraceOptions()
        with patch("shutil.which", return_value="/usr/bin/vtracer"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stderr="error msg", stdout="")
                with pytest.raises(RuntimeError, match="error msg"):
                    _trace_with_cli(tmp_path / "in.png", tmp_path / "out.svg", opts)


class TestTraceImageAdvancedOptions:
    def test_optimize_level_comprehensive(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = tmp_path / "normalized.png"
            with patch("vector_studio.tracer._trace_with_python_binding"):
                with patch("vector_studio.tracer.optimize_svg_comprehensive") as mock_opt:
                    with patch("vector_studio.tracer.svg_stats", return_value={}):
                        trace_image(img, out, optimize=True, optimize_level="comprehensive")
        mock_opt.assert_called_once_with(out, aggressive=False)

    def test_optimize_level_aggressive(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = tmp_path / "normalized.png"
            with patch("vector_studio.tracer._trace_with_python_binding"):
                with patch("vector_studio.tracer.optimize_svg_comprehensive") as mock_opt:
                    with patch("vector_studio.tracer.svg_stats", return_value={}):
                        trace_image(img, out, optimize=True, optimize_level="aggressive")
        mock_opt.assert_called_once_with(out, aggressive=True)

    def test_optimize_level_none(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = tmp_path / "normalized.png"
            with patch("vector_studio.tracer._trace_with_python_binding"):
                with patch("vector_studio.tracer.optimize_svg_file") as mock_opt:
                    with patch("vector_studio.tracer.svg_stats", return_value={}):
                        trace_image(img, out, optimize=True, optimize_level="none")
        mock_opt.assert_not_called()

    def test_stream_parameter_forces_streaming(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"
        normalized = tmp_path / "normalized.png"
        from PIL import Image
        Image.new("RGB", (10, 10)).save(normalized)

        with patch("vector_studio.performance.StreamingImageProcessor._should_stream", return_value=True):
            with patch("vector_studio.performance.StreamingImageProcessor.process_large_image", return_value=out):
                with patch("vector_studio.tracer.svg_stats", return_value={"paths": 3}):
                    with patch("vector_studio.tracer.prepare_input", return_value=normalized):
                        result = trace_image(img, out, stream=True)
        assert result.engine == "streaming-vtracer"

    def test_preview_mode_limits_size_and_skips_exports(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"
        normalized = tmp_path / "normalized.png"
        from PIL import Image
        Image.new("RGB", (10, 10)).save(normalized)

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = normalized
            with patch("vector_studio.tracer._trace_with_python_binding"):
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.svg_stats", return_value={}):
                        result = trace_image(img, out, preview_mode=True, export_pdf=True, export_png=True)
        assert result.svg_path == out
        assert result.pdf_path is None
        assert result.png_path is None

    def test_use_gpu_with_available_backend(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"
        normalized = tmp_path / "normalized.png"
        from PIL import Image
        Image.new("RGB", (10, 10)).save(normalized)

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = normalized
            with patch("vector_studio.tracer._trace_with_python_binding"):
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.svg_stats", return_value={}):
                        with patch("vector_studio.gpu_backend.detect_gpu") as mock_detect:
                            mock_detect.return_value = MagicMock(value="cuda")
                            with patch("vector_studio.gpu_backend.gpu_preprocess") as mock_gpu:
                                mock_gpu.return_value = MagicMock()
                                result = trace_image(img, out, use_gpu=True)
        assert result.svg_path == out

    def test_plugins_executed_in_pipeline(self, tmp_path):
        from vector_studio.plugin_interface import Plugin

        class TestPlugin(Plugin):
            name = "test"

            def preprocess(self, image, options):
                return image

            def postprocess(self, svg_path, options):
                return svg_path

        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"
        normalized = tmp_path / "normalized.png"
        from PIL import Image
        Image.new("RGB", (10, 10)).save(normalized)

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = normalized
            with patch("vector_studio.tracer._trace_with_python_binding"):
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.svg_stats", return_value={}):
                        result = trace_image(img, out, plugins=[TestPlugin()])
        assert result.svg_path == out

    def test_ai_simplify_in_pipeline(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"
        normalized = tmp_path / "normalized.png"
        from PIL import Image
        Image.new("RGB", (10, 10)).save(normalized)

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = normalized
            with patch("vector_studio.tracer._trace_with_python_binding"):
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.svg_stats", return_value={}):
                        with patch("vector_studio.ai_simplify.adaptive_simplify") as mock_simplify:
                            mock_img = MagicMock()
                            mock_simplify.return_value = mock_img
                            result = trace_image(img, out, ai_simplify=True, simplify_type="complex")
        assert result.svg_path == out

    def test_ai_ocr_in_pipeline(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"
        normalized = tmp_path / "normalized.png"
        from PIL import Image
        Image.new("RGB", (10, 10)).save(normalized)

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = normalized
            with patch("vector_studio.tracer._trace_with_python_binding"):
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.svg_stats", return_value={}):
                        with patch("vector_studio.ai_ocr.recognize_text_multilang", return_value=[{"text": "hi", "bbox": [0,0,10,10]}]):
                            with patch("vector_studio.ai_ocr.integrate_text_to_svg"):
                                result = trace_image(img, out, ai_ocr=True, ocr_lang="eng")
        assert result.svg_path == out
