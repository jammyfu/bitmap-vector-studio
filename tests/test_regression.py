from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vector_studio.models import TraceOptions, TraceResult
from vector_studio.tracer import trace_image


class TestRegressionBugFixes:
    """Tests that verify previously fixed bugs do not regress."""

    def test_output_suffix_always_svg(self, tmp_path: Path):
        """Regression: output path with non-svg suffix must be corrected."""
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.pdf"

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = tmp_path / "normalized.png"
            with patch("vector_studio.tracer._trace_with_python_binding"):
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.svg_stats", return_value={}):
                        result = trace_image(img, out)
        assert result.svg_path.suffix == ".svg"

    def test_trace_result_elapsed_non_negative(self, tmp_path: Path):
        """Regression: elapsed_seconds must never be negative."""
        img = tmp_path / "image.png"
        img.write_bytes(b"fake")
        out = tmp_path / "out.svg"

        with patch("vector_studio.tracer.prepare_input") as mock_prepare:
            mock_prepare.return_value = tmp_path / "normalized.png"
            with patch("vector_studio.tracer._trace_with_python_binding"):
                with patch("vector_studio.tracer.optimize_svg_file"):
                    with patch("vector_studio.tracer.svg_stats", return_value={}):
                        result = trace_image(img, out)
        assert result.elapsed_seconds >= 0

    def test_plugin_exception_does_not_crash_pipeline(self, tmp_path: Path):
        """Regression: a failing plugin must not abort conversion."""
        from vector_studio.plugin_interface import Plugin
        from vector_studio.plugins import PluginManager
        from PIL import Image

        class BadPlugin(Plugin):
            name = "bad"

            def preprocess(self, image, options):
                raise RuntimeError("plugin crash")

        manager = PluginManager()
        manager.register_plugin(BadPlugin)
        img = Image.new("RGB", (10, 10))
        with patch("vector_studio.plugins.logger"):
            result = manager.run_preprocess(img, {})
        assert result is img

    def test_empty_svg_stats_does_not_crash(self, tmp_path: Path):
        """Regression: svg_stats on empty/malformed SVG must not crash."""
        from vector_studio.svg_tools import svg_stats
        empty_svg = tmp_path / "empty.svg"
        empty_svg.write_text("<svg></svg>")
        stats = svg_stats(empty_svg)
        assert stats["paths"] == 0
        assert stats["groups"] == 0

    def test_config_load_malformed_returns_defaults(self, tmp_path: Path):
        """Regression: malformed config file must not crash, return defaults."""
        from vector_studio.config import Config
        bad = tmp_path / "bad.json"
        bad.write_text("not json")
        cfg = Config.load(bad)
        assert cfg.default_preset == "poster"

    def test_batch_skip_existing_does_not_overwrite(self, tmp_path: Path):
        """Regression: batch mode must skip existing SVGs by default."""
        from vector_studio.cli import app
        from typer.testing import CliRunner

        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (input_dir / "img.png").write_bytes(b"fake")
        (output_dir / "img.svg").write_text("<svg></svg>")

        with patch("vector_studio.cli.trace_image") as mock_trace:
            runner = CliRunner()
            result = runner.invoke(app, ["batch", str(input_dir), str(output_dir)])
        assert result.exit_code == 0
        assert "skipped" in result.output
        mock_trace.assert_not_called()

    def test_options_validation_rejects_invalid(self):
        """Regression: invalid options must raise ValueError early."""
        with pytest.raises(ValueError):
            TraceOptions(colormode="invalid").validate()
        with pytest.raises(ValueError):
            TraceOptions(filter_speckle=-1).validate()
        with pytest.raises(ValueError):
            TraceOptions(max_iterations=0).validate()

    def test_cli_region_invalid_format_exits(self, tmp_path: Path):
        """Regression: invalid --region format must exit with error."""
        from vector_studio.cli import app
        from typer.testing import CliRunner

        img = tmp_path / "img.png"
        img.write_bytes(b"fake")
        runner = CliRunner()
        result = runner.invoke(app, ["trace", str(img), "--region", "10,20,30"])
        assert result.exit_code == 1

    def test_api_bad_options_json_returns_400(self, tmp_path: Path):
        """Regression: bad options JSON in API must return 400."""
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient
        from vector_studio.api import app

        client = TestClient(app)
        img = tmp_path / "test.png"
        img.write_bytes(b"fake png data")
        with img.open("rb") as f:
            response = client.post(
                "/convert",
                files={"file": ("test.png", f, "image/png")},
                data={"options": "not-json"},
            )
        assert response.status_code == 400
        assert "Invalid options JSON" in response.json()["detail"]


class TestVersionCompatibility:
    def test_trace_options_vtracer_kwargs_stable(self):
        """Ensure vtracer_kwargs output keys remain stable across versions."""
        opts = TraceOptions()
        kwargs = opts.vtracer_kwargs()
        expected_keys = {
            "colormode", "hierarchical", "mode", "filter_speckle",
            "color_precision", "layer_difference", "corner_threshold",
            "length_threshold", "max_iterations", "splice_threshold",
            "path_precision",
        }
        assert set(kwargs.keys()) == expected_keys

    def test_trace_options_cli_args_stable(self, tmp_path: Path):
        """Ensure CLI args list remains stable across versions."""
        opts = TraceOptions(colormode="binary")
        args = opts.vtracer_cli_args(tmp_path / "in.png", tmp_path / "out.svg")
        assert "--colormode" in args
        assert "bw" in args
        assert "--input" in args
        assert "--output" in args

    def test_preset_names_unchanged(self):
        """Ensure built-in preset names remain available."""
        from vector_studio.presets import PRESETS
        expected = {"bw", "poster", "photo", "logo", "pixel_art", "scan"}
        assert expected.issubset(set(PRESETS.keys()))

    def test_plugin_interface_hooks_unchanged(self):
        """Ensure Plugin base class hooks remain stable."""
        from vector_studio.plugin_interface import Plugin
        assert hasattr(Plugin, "preprocess")
        assert hasattr(Plugin, "postprocess")
        assert hasattr(Plugin, "on_convert_complete")


class TestRegressionMore:
    def test_streaming_mode_does_not_crash_on_small_image(self, tmp_path: Path):
        """Regression: stream=True on small images should still work."""
        from PIL import Image
        img = tmp_path / "small.png"
        Image.new("RGB", (100, 100)).save(img)
        out = tmp_path / "out.svg"
        out.write_text("<svg></svg>")

        with patch("vector_studio.performance.StreamingImageProcessor._should_stream", return_value=False):
            with patch("vector_studio.tracer.prepare_input") as mock_prepare:
                mock_prepare.return_value = tmp_path / "normalized.png"
                Image.new("RGB", (10, 10)).save(mock_prepare.return_value)
                with patch("vector_studio.tracer._trace_with_python_binding"):
                    with patch("vector_studio.tracer.optimize_svg_file"):
                        with patch("vector_studio.tracer.svg_stats", return_value={"paths": 3}):
                            result = trace_image(img, out, stream=True)
        assert result.svg_path == out

    def test_batch_nested_directories_preserve_structure(self, tmp_path: Path):
        """Regression: batch recursive must preserve directory structure."""
        from vector_studio.cli import app
        from typer.testing import CliRunner

        input_dir = tmp_path / "input"
        input_dir.mkdir()
        sub = input_dir / "sub"
        sub.mkdir()
        (sub / "img.png").write_bytes(b"fake")
        output_dir = tmp_path / "output"

        mock_result = MagicMock()
        mock_result.svg_path = output_dir / "sub" / "img.svg"

        with patch("vector_studio.cli.trace_image", return_value=mock_result) as mock_trace:
            runner = CliRunner()
            result = runner.invoke(app, ["batch", str(input_dir), str(output_dir), "--recursive"])
        assert result.exit_code == 0
        assert mock_trace.call_count == 1
        passed_input = mock_trace.call_args[0][0]
        assert passed_input.parent.name == "sub"

    def test_api_temp_cleanup_on_exception(self, tmp_path: Path):
        """Regression: API temp files must be cleaned up even on errors."""
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient
        from vector_studio.api import app, _cleanup_api_temp

        client = TestClient(app)
        img = tmp_path / "test.png"
        img.write_bytes(b"fake png data")

        with patch("vector_studio.api.trace_image", side_effect=RuntimeError("boom")):
            with img.open("rb") as f:
                response = client.post(
                    "/convert",
                    files={"file": ("test.png", f, "image/png")},
                    data={"preset": "poster"},
                )
        assert response.status_code == 500
        _cleanup_api_temp()

    def test_options_posterize_none_does_not_crash(self):
        """Regression: posterize=None must be handled gracefully."""
        opts = TraceOptions(posterize=None)
        kwargs = opts.vtracer_kwargs()
        assert "posterize" not in kwargs or kwargs.get("posterize") is None

    def test_cli_batch_with_zero_images_exits_cleanly(self, tmp_path: Path):
        """Regression: batch on empty dir must exit 0, not crash."""
        from vector_studio.cli import app
        from typer.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(app, ["batch", str(tmp_path), str(tmp_path / "out")])
        assert result.exit_code == 0
        assert "No supported images" in result.output

    def test_svg_stats_on_malformed_xml(self, tmp_path: Path):
        """Regression: svg_stats on malformed XML must not crash."""
        from vector_studio.svg_tools import svg_stats
        bad_svg = tmp_path / "bad.svg"
        bad_svg.write_text("<svg><path d=\"M0 0\"><not-closed>")
        stats = svg_stats(bad_svg)
        assert isinstance(stats, dict)
        assert "paths" in stats
