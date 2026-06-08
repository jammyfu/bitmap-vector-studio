from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vector_studio.engines import (
    AutoTraceEngine,
    EngineBenchmark,
    EngineRegistry,
    PotraceEngine,
    VectorEngine,
    VTracerEngine,
)
from vector_studio.models import TraceOptions


class TestVectorEngineABC:
    def test_cannot_instantiate_abstract_base(self):
        with pytest.raises(TypeError):
            VectorEngine()

    def test_subclass_must_define_name(self):
        class BadEngine(VectorEngine):
            name = "bad"
            version = "0.1"
            supported_formats = [".png"]

            def convert(self, input_path, output_path, options):
                pass

        # Should be instantiable once required attrs are provided
        engine = BadEngine()
        assert engine.name == "bad"


class TestVTracerEngine:
    def test_name_and_version(self):
        engine = VTracerEngine()
        assert engine.name == "vtracer"
        assert engine.version == "1.0"

    def test_is_available_always_true(self):
        # VTracerEngine.is_available is inherited and always True
        assert VTracerEngine.is_available() is True

    def test_convert_uses_python_binding(self, tmp_path):
        engine = VTracerEngine()
        inp = tmp_path / "in.png"
        out = tmp_path / "out.svg"
        inp.write_bytes(b"fake")

        fake_vtracer = MagicMock()
        with patch.dict("sys.modules", {"vtracer": fake_vtracer}):
            engine.convert(inp, out, {"trace_options": TraceOptions()})
        fake_vtracer.convert_image_to_svg_py.assert_called_once()

    def test_convert_falls_back_to_cli(self, tmp_path):
        engine = VTracerEngine()
        inp = tmp_path / "in.png"
        out = tmp_path / "out.svg"
        inp.write_bytes(b"fake")

        with patch.dict("sys.modules", {"vtracer": None}):
            with patch("shutil.which", return_value="/usr/bin/vtracer"):
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
                    engine.convert(inp, out, {"trace_options": TraceOptions()})
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "/usr/bin/vtracer"

    def test_convert_raises_when_no_backend(self, tmp_path):
        engine = VTracerEngine()
        inp = tmp_path / "in.png"
        out = tmp_path / "out.svg"
        inp.write_bytes(b"fake")

        with patch.dict("sys.modules", {"vtracer": None}):
            with patch("shutil.which", return_value=None):
                with pytest.raises(RuntimeError, match="VTracer is not available"):
                    engine.convert(inp, out, {"trace_options": TraceOptions()})

    def test_get_info(self):
        engine = VTracerEngine()
        info = engine.get_info()
        assert info["name"] == "vtracer"
        assert info["available"] is True


class TestPotraceEngine:
    def test_name_and_availability(self):
        assert PotraceEngine.name == "potrace"

    def test_is_available_when_on_path(self):
        with patch("shutil.which", return_value="/usr/bin/potrace"):
            assert PotraceEngine.is_available() is True

    def test_is_available_when_missing(self):
        with patch("shutil.which", return_value=None):
            assert PotraceEngine.is_available() is False

    def test_convert_calls_potrace_cli(self, tmp_path):
        engine = PotraceEngine()
        inp = tmp_path / "in.png"
        out = tmp_path / "out.svg"
        # Create a minimal valid PNG via Pillow so Image.open succeeds
        from PIL import Image

        img = Image.new("RGB", (10, 10), color="white")
        inp = tmp_path / "in.png"
        img.save(inp, format="PNG")

        with patch("shutil.which", return_value="/usr/bin/potrace"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
                engine.convert(inp, out, {"turdsize": 4, "alphamax": 1.2, "opticurve": True})

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "potrace" in args
        assert "-s" in args
        assert "-O" in args
        assert "-t" in args
        assert "4" in args
        assert "-a" in args
        assert "1.2" in args

    def test_convert_raises_when_unavailable(self, tmp_path):
        engine = PotraceEngine()
        out = tmp_path / "out.svg"
        with patch("shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="potrace is not installed"):
                engine.convert(tmp_path / "in.png", out, {})

    def test_convert_raises_on_nonzero_returncode(self, tmp_path):
        engine = PotraceEngine()
        from PIL import Image

        img = Image.new("RGB", (10, 10), color="white")
        inp = tmp_path / "in.png"
        img.save(inp, format="PNG")
        out = tmp_path / "out.svg"

        with patch("shutil.which", return_value="/usr/bin/potrace"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stderr="potrace error", stdout="")
                with pytest.raises(RuntimeError, match="potrace error"):
                    engine.convert(inp, out, {})


class TestAutoTraceEngine:
    def test_name_and_availability(self):
        assert AutoTraceEngine.name == "autotrace"

    def test_is_available_when_on_path(self):
        with patch("shutil.which", return_value="/usr/bin/autotrace"):
            assert AutoTraceEngine.is_available() is True

    def test_is_available_when_missing(self):
        with patch("shutil.which", return_value=None):
            assert AutoTraceEngine.is_available() is False

    def test_convert_calls_autotrace_cli(self, tmp_path):
        engine = AutoTraceEngine()
        inp = tmp_path / "in.png"
        out = tmp_path / "out.svg"
        inp.write_bytes(b"fake")

        with patch("shutil.which", return_value="/usr/bin/autotrace"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
                engine.convert(inp, out, {"color_count": 8, "despeckle_level": 2, "corner_threshold": 90})

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "autotrace" in args
        assert "-output-file" in args
        assert str(out) in args
        assert "-color-count" in args
        assert "8" in args
        assert "-despeckle-level" in args
        assert "2" in args
        assert "-corner-threshold" in args
        assert "90" in args

    def test_convert_raises_when_unavailable(self, tmp_path):
        engine = AutoTraceEngine()
        out = tmp_path / "out.svg"
        with patch("shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="autotrace is not installed"):
                engine.convert(tmp_path / "in.png", out, {})

    def test_convert_raises_on_nonzero_returncode(self, tmp_path):
        engine = AutoTraceEngine()
        inp = tmp_path / "in.png"
        out = tmp_path / "out.svg"
        inp.write_bytes(b"fake")

        with patch("shutil.which", return_value="/usr/bin/autotrace"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stderr="autotrace error", stdout="")
                with pytest.raises(RuntimeError, match="autotrace error"):
                    engine.convert(inp, out, {})


class TestEngineRegistry:
    def test_default_engines_registered(self):
        registry = EngineRegistry()
        engines = registry.list_engines()
        names = {e["name"] for e in engines}
        assert names >= {"vtracer", "potrace", "autotrace"}

    def test_get_engine_returns_instance(self):
        registry = EngineRegistry()
        engine = registry.get_engine("vtracer")
        assert isinstance(engine, VTracerEngine)

    def test_get_engine_unknown_raises(self):
        registry = EngineRegistry()
        with pytest.raises(ValueError, match="Unknown engine"):
            registry.get_engine("nonexistent")

    def test_register_custom_engine(self):
        class CustomEngine(VectorEngine):
            name = "custom"
            version = "0.1"
            supported_formats = [".png"]

            def convert(self, input_path, output_path, options):
                return {"engine": "custom"}

        registry = EngineRegistry()
        registry.register(CustomEngine)
        engine = registry.get_engine("custom")
        assert isinstance(engine, CustomEngine)

    def test_get_best_engine_for_logo(self):
        registry = EngineRegistry()
        with patch.object(PotraceEngine, "is_available", return_value=True):
            engine = registry.get_best_engine(Path("/fake.png"), image_type="logo")
            assert isinstance(engine, PotraceEngine)

    def test_get_best_engine_for_photo(self):
        registry = EngineRegistry()
        with patch.object(VTracerEngine, "is_available", return_value=True):
            engine = registry.get_best_engine(Path("/fake.png"), image_type="photo")
            assert isinstance(engine, VTracerEngine)

    def test_get_best_engine_for_complex(self):
        registry = EngineRegistry()
        with patch.object(AutoTraceEngine, "is_available", return_value=True):
            engine = registry.get_best_engine(Path("/fake.png"), image_type="complex")
            assert isinstance(engine, AutoTraceEngine)

    def test_get_best_engine_fallback_chain(self):
        registry = EngineRegistry()
        with patch.object(VTracerEngine, "is_available", return_value=False):
            with patch.object(PotraceEngine, "is_available", return_value=True):
                engine = registry.get_best_engine(Path("/fake.png"), image_type="photo")
                assert isinstance(engine, PotraceEngine)

    def test_detect_image_type_logo(self, tmp_path):
        from PIL import Image

        registry = EngineRegistry()
        img = Image.new("1", (10, 10), color=1)
        p = tmp_path / "logo.png"
        img.save(p, format="PNG")
        assert registry._detect_image_type(p) == "logo"

    def test_detect_image_type_photo(self, tmp_path):
        from PIL import Image

        registry = EngineRegistry()
        img = Image.new("RGB", (2000, 2000), color="red")
        p = tmp_path / "photo.png"
        img.save(p, format="PNG")
        assert registry._detect_image_type(p) == "photo"


class TestEngineBenchmark:
    def test_compare_engines_runs_all_available(self, tmp_path):
        from PIL import Image

        img = Image.new("RGB", (10, 10), color="white")
        inp = tmp_path / "test.png"
        img.save(inp, format="PNG")

        benchmark = EngineBenchmark()
        with patch.object(VTracerEngine, "convert") as mock_convert:
            with patch.object(PotraceEngine, "convert") as mock_potrace:
                with patch.object(AutoTraceEngine, "convert") as mock_autotrace:
                    # Write a minimal SVG so svg_stats works
                    def write_svg(src, dst, opts):
                        Path(dst).write_text('<svg><path d="M0 0"/></svg>', encoding="utf-8")
                        return {}

                    mock_convert.side_effect = write_svg
                    mock_potrace.side_effect = write_svg
                    mock_autotrace.side_effect = write_svg

                    results = benchmark.compare_engines(inp, engines=["vtracer", "potrace", "autotrace"])

        assert len(results) == 3
        names = {r["engine"] for r in results}
        assert names == {"vtracer", "potrace", "autotrace"}

    def test_compare_engines_handles_errors(self, tmp_path):
        from PIL import Image

        img = Image.new("RGB", (10, 10), color="white")
        inp = tmp_path / "test.png"
        img.save(inp, format="PNG")

        benchmark = EngineBenchmark()
        with patch.object(VTracerEngine, "convert", side_effect=RuntimeError("boom")):
            results = benchmark.compare_engines(inp, engines=["vtracer"])

        assert len(results) == 1
        assert results[0]["engine"] == "vtracer"
        assert "error" in results[0]

    def test_run_full_benchmark(self, tmp_path):
        from PIL import Image

        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        img = Image.new("RGB", (10, 10), color="white")
        img.save(input_dir / "a.png", format="PNG")

        benchmark = EngineBenchmark()
        with patch.object(VTracerEngine, "convert") as mock_convert:

            def write_svg(src, dst, opts):
                Path(dst).write_text('<svg><path d="M0 0"/></svg>', encoding="utf-8")
                return {}

            mock_convert.side_effect = write_svg
            summary = benchmark.run_full_benchmark(input_dir, output_dir, engines=["vtracer"])

        assert summary["images_tested"] == 1
        assert "vtracer" in summary["engines"]
        assert "vtracer" in summary
        assert summary["vtracer"]["success_rate"] == 1.0


class TestTracerEngineIntegration:
    def test_trace_image_with_vtracer_engine(self, tmp_path):
        from vector_studio.tracer import trace_image

        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = tmp_path / "normalized.png"
            with patch("vector_studio.tracer._trace_with_python_binding") as mock_trace:
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.svg_stats", return_value={}):
                        result = trace_image(img, out, engine="vtracer")
        mock_trace.assert_called_once()
        assert result.engine == "python-vtracer"

    def test_trace_image_with_unknown_engine_fallback(self, tmp_path):
        from vector_studio.tracer import trace_image

        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = tmp_path / "normalized.png"
            with patch("vector_studio.tracer._trace_with_python_binding") as mock_trace:
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.svg_stats", return_value={}):
                        result = trace_image(img, out, engine="nonexistent")
        mock_trace.assert_called_once()
        assert result.engine == "python-vtracer"

    def test_trace_image_with_unavailable_engine_fallback(self, tmp_path):
        from vector_studio.tracer import trace_image

        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = tmp_path / "normalized.png"
            with patch("vector_studio.tracer._trace_with_python_binding") as mock_trace:
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.svg_stats", return_value={}):
                        with patch.object(PotraceEngine, "is_available", return_value=False):
                            result = trace_image(img, out, engine="potrace")
        mock_trace.assert_called_once()
        assert result.engine == "python-vtracer"
