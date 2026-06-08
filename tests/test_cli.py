from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from vector_studio.cli import app
from vector_studio.models import TraceOptions, TraceResult


runner = CliRunner()


class TestPresetsCommand:
    def test_presets_lists_built_in_presets(self):
        result = runner.invoke(app, ["presets"])
        assert result.exit_code == 0
        assert "bw" in result.output
        assert "poster" in result.output
        assert "photo" in result.output


class TestTraceCommand:
    def test_trace_missing_input_fails(self):
        result = runner.invoke(app, ["trace", "/nonexistent/image.png"])
        assert result.exit_code != 0

    def test_trace_basic_invocation(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"

        mock_result = TraceResult(
            input_path=img,
            svg_path=out,
            engine="python-vtracer",
            elapsed_seconds=1.5,
            stats={"paths": 5},
        )

        with patch("vector_studio.cli.trace_image", return_value=mock_result) as mock_trace:
            result = runner.invoke(app, ["trace", str(img), "--output", str(out)])

        assert result.exit_code == 0
        mock_trace.assert_called_once()
        assert out.name in result.output or "Done" in result.output

    def test_trace_uses_preset(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")

        mock_result = TraceResult(
            input_path=img,
            svg_path=img.with_suffix(".svg"),
            engine="python-vtracer",
            elapsed_seconds=1.0,
            stats={},
        )

        with patch("vector_studio.cli.trace_image", return_value=mock_result) as mock_trace:
            runner.invoke(app, ["trace", str(img), "--preset", "bw"])

        passed_options = mock_trace.call_args[0][2]
        assert passed_options.colormode == "binary"

    def test_trace_parameter_overrides(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")

        mock_result = TraceResult(
            input_path=img,
            svg_path=img.with_suffix(".svg"),
            engine="python-vtracer",
            elapsed_seconds=1.0,
            stats={},
        )

        with patch("vector_studio.cli.trace_image", return_value=mock_result) as mock_trace:
            runner.invoke(app, [
                "trace", str(img),
                "--colormode", "binary",
                "--filter-speckle", "8",
                "--color-precision", "4",
                "--layer-difference", "32",
                "--corner-threshold", "90",
                "--length-threshold", "5.5",
                "--max-iterations", "20",
                "--splice-threshold", "60",
                "--path-precision", "5",
                "--denoise",
                "--posterize", "4",
                "--max-input-side", "1024",
            ])

        passed_options = mock_trace.call_args[0][2]
        assert passed_options.colormode == "binary"
        assert passed_options.filter_speckle == 8
        assert passed_options.color_precision == 4
        assert passed_options.layer_difference == 32
        assert passed_options.corner_threshold == 90
        assert passed_options.length_threshold == 5.5
        assert passed_options.max_iterations == 20
        assert passed_options.splice_threshold == 60
        assert passed_options.path_precision == 5
        assert passed_options.denoise is True
        assert passed_options.posterize == 4
        assert passed_options.max_input_side == 1024

    def test_trace_defaults_when_no_overrides(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")

        mock_result = TraceResult(
            input_path=img,
            svg_path=img.with_suffix(".svg"),
            engine="python-vtracer",
            elapsed_seconds=1.0,
            stats={},
        )

        with patch("vector_studio.cli.trace_image", return_value=mock_result) as mock_trace:
            runner.invoke(app, ["trace", str(img)])

        passed_options = mock_trace.call_args[0][2]
        assert passed_options.colormode == "color"
        assert passed_options.denoise is False
        assert passed_options.posterize is None

    def test_trace_optimize_default_true(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")

        mock_result = TraceResult(
            input_path=img,
            svg_path=img.with_suffix(".svg"),
            engine="python-vtracer",
            elapsed_seconds=1.0,
            stats={},
        )

        with patch("vector_studio.cli.trace_image", return_value=mock_result) as mock_trace:
            runner.invoke(app, ["trace", str(img)])

        assert mock_trace.call_args[1]["optimize"] is True

    def test_trace_no_optimize(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")

        mock_result = TraceResult(
            input_path=img,
            svg_path=img.with_suffix(".svg"),
            engine="python-vtracer",
            elapsed_seconds=1.0,
            stats={},
        )

        with patch("vector_studio.cli.trace_image", return_value=mock_result) as mock_trace:
            runner.invoke(app, ["trace", str(img), "--no-optimize"])

        assert mock_trace.call_args[1]["optimize"] is False

    def test_trace_name_layers(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")

        mock_result = TraceResult(
            input_path=img,
            svg_path=img.with_suffix(".svg"),
            engine="python-vtracer",
            elapsed_seconds=1.0,
            stats={},
        )

        with patch("vector_studio.cli.trace_image", return_value=mock_result) as mock_trace:
            runner.invoke(app, ["trace", str(img), "--name-layers"])

        assert mock_trace.call_args[1]["name_layers"] is True

    def test_trace_export_options(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")

        mock_result = TraceResult(
            input_path=img,
            svg_path=img.with_suffix(".svg"),
            engine="python-vtracer",
            elapsed_seconds=1.0,
            stats={},
            pdf_path=img.with_suffix(".pdf"),
            png_path=img.with_suffix(".png"),
            eps_path=img.with_suffix(".eps"),
        )

        with patch("vector_studio.cli.trace_image", return_value=mock_result) as mock_trace:
            result = runner.invoke(app, [
                "trace", str(img),
                "--export-pdf",
                "--export-png",
                "--export-eps",
            ])

        assert mock_trace.call_args[1]["export_pdf"] is True
        assert mock_trace.call_args[1]["export_png"] is True
        assert mock_trace.call_args[1]["export_eps"] is True
        assert "PDF:" in result.output
        assert "PNG:" in result.output
        assert "EPS:" in result.output

    def test_trace_open_editor_with_name(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        svg = tmp_path / "out.svg"
        svg.write_text("<svg></svg>")

        mock_result = TraceResult(
            input_path=img,
            svg_path=svg,
            engine="python-vtracer",
            elapsed_seconds=1.0,
            stats={},
        )

        with patch("vector_studio.cli.trace_image", return_value=mock_result):
            with patch("vector_studio.cli.open_with_editor") as mock_open:
                result = runner.invoke(app, ["trace", str(img), "--output", str(svg), "--open", "inkscape"])

        assert result.exit_code == 0
        mock_open.assert_called_once_with(svg, "inkscape")

    def test_trace_open_default_editor(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        svg = tmp_path / "out.svg"
        svg.write_text("<svg></svg>")

        mock_result = TraceResult(
            input_path=img,
            svg_path=svg,
            engine="python-vtracer",
            elapsed_seconds=1.0,
            stats={},
        )

        with patch("vector_studio.cli.trace_image", return_value=mock_result):
            with patch("vector_studio.cli.open_with_default_editor") as mock_open:
                result = runner.invoke(app, ["trace", str(img), "--output", str(svg), "--open", ""])

        assert result.exit_code == 0
        mock_open.assert_called_once_with(svg)

    def test_trace_open_editor_failure_graceful(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        svg = tmp_path / "out.svg"
        svg.write_text("<svg></svg>")

        mock_result = TraceResult(
            input_path=img,
            svg_path=svg,
            engine="python-vtracer",
            elapsed_seconds=1.0,
            stats={},
        )

        with patch("vector_studio.cli.trace_image", return_value=mock_result):
            with patch("vector_studio.cli.open_with_default_editor", side_effect=RuntimeError("boom")):
                result = runner.invoke(app, ["trace", str(img), "--output", str(svg), "--open", ""])

        assert result.exit_code == 0
        assert "Failed to open editor" in result.output


class TestBatchCommand:
    def test_batch_no_images_warns(self, tmp_path):
        result = runner.invoke(app, ["batch", str(tmp_path), str(tmp_path / "out")])
        assert result.exit_code == 0
        assert "No supported images found" in result.output

    def test_batch_converts_images(self, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        (input_dir / "img1.png").write_bytes(b"fake")
        (input_dir / "img2.jpg").write_bytes(b"fake")

        mock_result = MagicMock()
        mock_result.svg_path = output_dir / "img1.svg"

        with patch("vector_studio.cli.trace_image", return_value=mock_result) as mock_trace:
            result = runner.invoke(app, ["batch", str(input_dir), str(output_dir)])

        assert result.exit_code == 0
        assert mock_trace.call_count == 2

    def test_batch_recursive(self, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        subdir = input_dir / "sub"
        subdir.mkdir()
        (subdir / "img.png").write_bytes(b"fake")
        output_dir = tmp_path / "output"

        mock_result = MagicMock()
        mock_result.svg_path = output_dir / "sub" / "img.svg"

        with patch("vector_studio.cli.trace_image", return_value=mock_result) as mock_trace:
            result = runner.invoke(app, ["batch", str(input_dir), str(output_dir), "--recursive"])

        assert result.exit_code == 0
        assert mock_trace.call_count == 1

    def test_batch_skip_existing(self, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (input_dir / "img.png").write_bytes(b"fake")
        (output_dir / "img.svg").write_text("<svg></svg>")

        with patch("vector_studio.cli.trace_image") as mock_trace:
            result = runner.invoke(app, ["batch", str(input_dir), str(output_dir)])

        assert result.exit_code == 0
        assert "skipped" in result.output
        mock_trace.assert_not_called()

    def test_batch_overwrite(self, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (input_dir / "img.png").write_bytes(b"fake")
        (output_dir / "img.svg").write_text("<svg></svg>")

        mock_result = MagicMock()
        mock_result.svg_path = output_dir / "img.svg"

        with patch("vector_studio.cli.trace_image", return_value=mock_result) as mock_trace:
            result = runner.invoke(app, ["batch", str(input_dir), str(output_dir), "--overwrite"])

        assert result.exit_code == 0
        assert "ok" in result.output
        mock_trace.assert_called_once()

    def test_batch_name_layers_passed(self, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        (input_dir / "img.png").write_bytes(b"fake")

        mock_result = MagicMock()
        mock_result.svg_path = output_dir / "img.svg"

        with patch("vector_studio.cli.trace_image", return_value=mock_result) as mock_trace:
            runner.invoke(app, ["batch", str(input_dir), str(output_dir), "--name-layers"])

        assert mock_trace.call_args[1]["name_layers"] is True

    def test_batch_export_options_passed(self, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        (input_dir / "img.png").write_bytes(b"fake")

        mock_result = MagicMock()
        mock_result.svg_path = output_dir / "img.svg"

        with patch("vector_studio.cli.trace_image", return_value=mock_result) as mock_trace:
            runner.invoke(app, [
                "batch", str(input_dir), str(output_dir),
                "--export-pdf",
                "--export-png",
            ])

        assert mock_trace.call_args[1]["export_pdf"] is True
        assert mock_trace.call_args[1]["export_png"] is True

    def test_batch_open_editor(self, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (input_dir / "img.png").write_bytes(b"fake")
        svg = output_dir / "img.svg"

        mock_result = MagicMock()
        mock_result.svg_path = svg

        with patch("vector_studio.cli.trace_image", return_value=mock_result) as mock_trace:
            with patch("vector_studio.cli.open_with_default_editor") as mock_open:
                result = runner.invoke(app, ["batch", str(input_dir), str(output_dir), "--open"])

        assert result.exit_code == 0, result.output
        mock_trace.assert_called_once()
        mock_open.assert_called_once_with(svg)

    def test_batch_failure_counted(self, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        (input_dir / "img.png").write_bytes(b"fake")

        with patch("vector_studio.cli.trace_image", side_effect=RuntimeError("boom")):
            result = runner.invoke(app, ["batch", str(input_dir), str(output_dir)])

        assert result.exit_code == 1
        assert "failed" in result.output


class TestSearchCommand:
    def test_search_quick(self, tmp_path):
        img = tmp_path / "img.png"
        img.write_bytes(b"fake image")
        out_dir = tmp_path / "out"

        mock_result = TraceResult(
            input_path=img,
            svg_path=out_dir / "quick_logo_001.svg",
            engine="python-vtracer",
            elapsed_seconds=1.0,
            stats={"paths": 5},
        )

        with patch("vector_studio.cli.quick_search", return_value=("logo", out_dir / "best.svg", 42.0)) as mock_search:
            with patch("vector_studio.cli.svg_stats", return_value={"paths": 5}):
                result = runner.invoke(app, ["search", str(img), "--output-dir", str(out_dir), "--quick"])

        assert result.exit_code == 0
        mock_search.assert_called_once()
        assert "Best preset" in result.output
        assert "logo" in result.output

    def test_search_full(self, tmp_path):
        img = tmp_path / "img.png"
        img.write_bytes(b"fake image")
        out_dir = tmp_path / "out"

        best_opts = TraceOptions(color_precision=6, filter_speckle=2)

        with patch("vector_studio.cli.search_best_params", return_value=(best_opts, out_dir / "best.svg", 55.0, [])) as mock_search:
            with patch("vector_studio.cli.svg_stats", return_value={"paths": 5}):
                result = runner.invoke(app, ["search", str(img), "--output-dir", str(out_dir), "--max", "10"])

        assert result.exit_code == 0
        mock_search.assert_called_once()
        assert "Best score" in result.output
        assert "55.0" in result.output


class TestQueueCommands:
    def test_queue_add(self, tmp_path):
        img = tmp_path / "img.png"
        img.write_bytes(b"fake image")
        out = tmp_path / "out.svg"

        mock_result = TraceResult(
            input_path=img,
            svg_path=out,
            engine="python-vtracer",
            elapsed_seconds=0.5,
            stats={"paths": 3},
        )

        with patch("vector_studio.task_queue.trace_image", return_value=mock_result):
            with patch("vector_studio.history.record_task") as mock_record:
                result = runner.invoke(app, ["queue", "add", str(img), "--output", str(out), "--preset", "logo"])

        assert result.exit_code == 0
        assert "Done" in result.output
        mock_record.assert_called_once()

    def test_queue_status(self):
        result = runner.invoke(app, ["queue", "status"])
        assert result.exit_code == 0
        assert "No persistent queue" in result.output

    def test_queue_start(self):
        result = runner.invoke(app, ["queue", "start"])
        assert result.exit_code == 0
        assert "Queue start is handled automatically" in result.output

    def test_queue_report(self, tmp_path):
        report = tmp_path / "report.csv"
        result = runner.invoke(app, ["queue", "report", "--path", str(report)])
        assert result.exit_code == 0
        assert "No persistent queue state" in result.output


class TestBatchWorkers:
    def test_batch_with_workers_uses_task_queue(self, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        (input_dir / "img1.png").write_bytes(b"fake")
        (input_dir / "img2.png").write_bytes(b"fake")

        mock_result = TraceResult(
            input_path=input_dir / "img1.png",
            svg_path=output_dir / "img1.svg",
            engine="python-vtracer",
            elapsed_seconds=0.5,
            stats={"paths": 3},
        )

        with patch("vector_studio.task_queue.trace_image", return_value=mock_result):
            result = runner.invoke(app, ["batch", str(input_dir), str(output_dir), "--workers", "2"])

        assert result.exit_code == 0
        assert "ok" in result.output

    def test_batch_with_retry(self, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        (input_dir / "img.png").write_bytes(b"fake")

        with patch("vector_studio.cli.trace_image", side_effect=RuntimeError("boom")):
            result = runner.invoke(app, ["batch", str(input_dir), str(output_dir), "--workers", "2", "--retry", "1"])

        assert result.exit_code == 1
        assert "failed" in result.output
