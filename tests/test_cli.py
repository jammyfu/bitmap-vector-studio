from pathlib import Path
from unittest.mock import MagicMock, patch

import os
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


class TestApiCommand:
    def test_api_command_missing_uvicorn(self):
        with patch("vector_studio.cli.uvicorn", None):
            result = runner.invoke(app, ["api"])
        assert result.exit_code == 1
        assert "API dependencies are missing" in result.output

    def test_api_command_starts_server(self):
        with patch("vector_studio.cli.uvicorn.run") as mock_run:
            result = runner.invoke(app, ["api", "--port", "9999", "--workers", "2"])
        assert result.exit_code == 0
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["port"] == 9999
        assert call_kwargs["workers"] == 2
        assert call_kwargs["host"] == "0.0.0.0"

    def test_api_global_flag_starts_server(self):
        with patch("vector_studio.cli.uvicorn.run") as mock_run:
            result = runner.invoke(app, ["--api", "--port", "8888"])
        assert result.exit_code == 0
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["port"] == 8888

    def test_api_global_flag_missing_uvicorn(self):
        with patch("vector_studio.cli.uvicorn", None):
            result = runner.invoke(app, ["--api"])
        assert result.exit_code == 1
        assert "API dependencies are missing" in result.output


class TestLivePreviewOption:
    def test_trace_live_preview(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"
        out.write_text("<svg></svg>")

        mock_result = TraceResult(
            input_path=img,
            svg_path=out,
            engine="python-vtracer",
            elapsed_seconds=0.2,
            stats={},
        )

        with patch("vector_studio.live_preview.LivePreviewEngine") as mock_engine_cls:
            mock_engine = mock_engine_cls.return_value
            mock_engine.generate_preview.return_value = (out, 0.2)
            result = runner.invoke(app, ["trace", str(img), "--output", str(out), "--live-preview"])

        assert result.exit_code == 0
        assert "Preview" in result.output
        mock_engine.generate_preview.assert_called_once()


class TestRegionOption:
    def test_trace_region_rect(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        out = tmp_path / "out.svg"
        out.write_text("<svg></svg>")

        mock_result = TraceResult(
            input_path=img,
            svg_path=out,
            engine="python-vtracer",
            elapsed_seconds=0.5,
            stats={"paths": 3},
        )

        with patch("vector_studio.region_trace.region_trace", return_value=mock_result) as mock_region:
            result = runner.invoke(app, ["trace", str(img), "--output", str(out), "--region", "10,20,30,40"])

        assert result.exit_code == 0
        assert "Done" in result.output
        mock_region.assert_called_once()
        passed_region = mock_region.call_args[0][1]
        assert passed_region.x == 10
        assert passed_region.y == 20
        assert passed_region.width == 30
        assert passed_region.height == 40
        assert passed_region.shape == "rect"

    def test_trace_region_invalid_format(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        result = runner.invoke(app, ["trace", str(img), "--region", "10,20,30"])
        assert result.exit_code == 1
        assert "must be x,y,w,h" in result.output or "Error" in result.output

    def test_trace_region_invalid_values(self, tmp_path):
        img = tmp_path / "image.png"
        img.write_bytes(b"fake image data")
        result = runner.invoke(app, ["trace", str(img), "--region", "a,b,c,d"])
        assert result.exit_code == 1
        assert "must be integers" in result.output or "Error" in result.output


class TestBenchmarkCommand:
    def test_benchmark_runs(self, tmp_path):
        from PIL import Image
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
            result = runner.invoke(app, ["benchmark", str(img), "--runs", "2"])
        assert result.exit_code == 0
        assert "Benchmark" in result.output
        assert "Min" in result.output
        assert "Mean" in result.output

    def test_benchmark_with_gpu(self, tmp_path):
        from PIL import Image
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
            result = runner.invoke(app, ["benchmark", str(img), "--runs", "1", "--gpu"])
        assert result.exit_code == 0

    def test_benchmark_with_stream(self, tmp_path):
        from PIL import Image
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
            result = runner.invoke(app, ["benchmark", str(img), "--runs", "1", "--stream"])
        assert result.exit_code == 0


class TestConfigCommands:
    def test_config_show(self, tmp_path):
        from vector_studio.config import Config
        cfg = Config(default_preset="logo")
        config_path = tmp_path / "config.json"
        cfg.save(config_path)
        result = runner.invoke(app, ["config", "show", "--config", str(config_path)])
        assert result.exit_code == 0
        assert "logo" in result.output

    def test_config_show_invalid(self, tmp_path):
        from vector_studio.config import Config
        cfg = Config(default_optimize_level="super")
        config_path = tmp_path / "config.json"
        cfg.save(config_path)
        result = runner.invoke(app, ["config", "show", "--config", str(config_path)])
        assert result.exit_code == 1
        assert "Validation error" in result.output

    def test_config_init(self, tmp_path):
        config_path = tmp_path / "config.json"
        result = runner.invoke(app, ["config", "init", "--path", str(config_path)])
        assert result.exit_code == 0
        assert config_path.exists()

    def test_config_init_force(self, tmp_path):
        config_path = tmp_path / "config.json"
        config_path.write_text("{}")
        result = runner.invoke(app, ["config", "init", "--path", str(config_path), "--force"])
        assert result.exit_code == 0

    def test_config_init_no_force(self, tmp_path):
        config_path = tmp_path / "config.json"
        config_path.write_text("{}")
        result = runner.invoke(app, ["config", "init", "--path", str(config_path)])
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_config_set(self, tmp_path):
        from vector_studio.config import Config
        cfg = Config()
        config_path = tmp_path / "config.json"
        cfg.save(config_path)
        result = runner.invoke(app, ["config", "set", "default_preset", "logo", "--path", str(config_path)])
        assert result.exit_code == 0
        loaded = Config.load(config_path)
        assert loaded.default_preset == "logo"

    def test_config_set_unknown_key(self, tmp_path):
        from vector_studio.config import Config
        cfg = Config()
        config_path = tmp_path / "config.json"
        cfg.save(config_path)
        result = runner.invoke(app, ["config", "set", "bad_key", "value", "--path", str(config_path)])
        assert result.exit_code == 1
        assert "Unknown config key" in result.output

    def test_config_set_bool(self, tmp_path):
        from vector_studio.config import Config
        cfg = Config()
        config_path = tmp_path / "config.json"
        cfg.save(config_path)
        result = runner.invoke(app, ["config", "set", "smart_remove_bg", "true", "--path", str(config_path)])
        assert result.exit_code == 0
        loaded = Config.load(config_path)
        assert loaded.smart_remove_bg is True

    def test_config_set_int(self, tmp_path):
        from vector_studio.config import Config
        cfg = Config()
        config_path = tmp_path / "config.json"
        cfg.save(config_path)
        result = runner.invoke(app, ["config", "set", "max_workers", "8", "--path", str(config_path)])
        assert result.exit_code == 0
        loaded = Config.load(config_path)
        assert loaded.max_workers == 8

    def test_config_set_list(self, tmp_path):
        from vector_studio.config import Config
        cfg = Config()
        config_path = tmp_path / "config.json"
        cfg.save(config_path)
        result = runner.invoke(app, ["config", "set", "enabled_plugins", "watermark,resize", "--path", str(config_path)])
        assert result.exit_code == 0
        loaded = Config.load(config_path)
        assert loaded.enabled_plugins == ["watermark", "resize"]

    def test_config_validate(self, tmp_path):
        from vector_studio.config import Config
        cfg = Config()
        config_path = tmp_path / "config.json"
        cfg.save(config_path)
        result = runner.invoke(app, ["config", "validate", "--path", str(config_path)])
        assert result.exit_code == 0
        assert "valid" in result.output.lower()


class TestPluginCommands:
    def test_plugin_list(self):
        result = runner.invoke(app, ["plugin", "list"])
        assert result.exit_code == 0
        assert "watermark" in result.output or "resize" in result.output or "No plugins" in result.output

    def test_plugin_enable_disable(self, tmp_path):
        from vector_studio.config import Config
        from vector_studio.plugins import PluginManager
        from vector_studio.builtin_plugins.watermark_plugin import WatermarkPlugin
        cfg = Config()
        config_path = tmp_path / "config.json"
        cfg.save(config_path)
        with patch("vector_studio.cli.Config.load", return_value=cfg):
            with patch("vector_studio.cli.Config.save"):
                with patch.object(PluginManager, "_plugin_classes", {"watermark": WatermarkPlugin}):
                    with patch.object(PluginManager, "_enabled", set()):
                        result = runner.invoke(app, ["plugin", "enable", "watermark"])
        assert result.exit_code == 0
        assert "Enabled" in result.output

    def test_plugin_enable_unknown(self):
        result = runner.invoke(app, ["plugin", "enable", "nonexistent"])
        assert result.exit_code == 1
        assert "Unknown" in result.output

    def test_plugin_disable_unknown(self):
        result = runner.invoke(app, ["plugin", "disable", "nonexistent"])
        assert result.exit_code == 1
        assert "Unknown" in result.output

    def test_plugin_install(self, tmp_path):
        plugin_file = tmp_path / "my_plugin.py"
        plugin_file.write_text(
            "from vector_studio.plugin_interface import Plugin\n"
            "class MyPlugin(Plugin):\n"
            "    name = 'my_plugin'\n"
        )
        with patch("vector_studio.plugins._user_plugin_dir", return_value=tmp_path / "plugins"):
            result = runner.invoke(app, ["plugin", "install", str(plugin_file)])
        assert result.exit_code == 0
        assert "Installed" in result.output


class TestWorkspaceCommands:
    def test_workspace_list_empty(self):
        with patch("vector_studio.workspace._default_workspace_dir", return_value=Path("/tmp/nonexistent_workspaces")):
            result = runner.invoke(app, ["workspace", "list"])
        assert result.exit_code == 0
        assert "No saved workspaces" in result.output or "Workspace" in result.output

    def test_workspace_save_and_load(self, tmp_path):
        ws_dir = tmp_path / "workspaces"
        ws_dir.mkdir()
        with patch("vector_studio.workspace._default_workspace_dir", return_value=ws_dir):
            result = runner.invoke(app, ["workspace", "save", "test_ws", "--preset", "logo"])
            assert result.exit_code == 0
            assert "saved" in result.output

            result = runner.invoke(app, ["workspace", "load", "test_ws"])
            assert result.exit_code == 0
            assert "logo" in result.output

    def test_workspace_load_missing(self):
        with patch("vector_studio.workspace._default_workspace_dir", return_value=Path("/tmp/nonexistent_workspaces")):
            result = runner.invoke(app, ["workspace", "load", "missing_ws"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_workspace_delete(self, tmp_path):
        ws_dir = tmp_path / "workspaces"
        ws_dir.mkdir()
        with patch("vector_studio.workspace._default_workspace_dir", return_value=ws_dir):
            runner.invoke(app, ["workspace", "save", "del_ws"])
            result = runner.invoke(app, ["workspace", "delete", "del_ws"])
            assert result.exit_code == 0
            assert "Deleted" in result.output

    def test_workspace_delete_missing(self):
        with patch("vector_studio.workspace._default_workspace_dir", return_value=Path("/tmp/nonexistent_workspaces")):
            result = runner.invoke(app, ["workspace", "delete", "missing_ws"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()


class TestOcrCommands:
    def test_ocr_detect(self, tmp_path):
        img = tmp_path / "img.png"
        from PIL import Image
        Image.new("RGB", (100, 100)).save(img)
        with patch("vector_studio.ai_ocr.detect_text_regions", return_value=[{"bbox": [0,0,10,10], "confidence": 0.9}]):
            result = runner.invoke(app, ["ocr", "detect", str(img)])
        assert result.exit_code == 0
        assert "Text regions" in result.output or "regions" in result.output

    def test_ocr_detect_vertical(self, tmp_path):
        img = tmp_path / "img.png"
        from PIL import Image
        Image.new("RGB", (100, 100)).save(img)
        with patch("vector_studio.ai_ocr.detect_vertical_text", return_value=[{"bbox": [0,0,10,10], "confidence": 0.9, "vertical": True}]):
            result = runner.invoke(app, ["ocr", "detect", str(img), "--vertical"])
        assert result.exit_code == 0

    def test_ocr_recognize(self, tmp_path):
        img = tmp_path / "img.png"
        from PIL import Image
        Image.new("RGB", (100, 100)).save(img)
        with patch("vector_studio.ai_ocr.recognize_text_multilang", return_value=[{"text": "hello", "bbox": [0,0,10,10], "confidence": 0.9, "lang": "eng"}]):
            result = runner.invoke(app, ["ocr", "recognize", str(img)])
        assert result.exit_code == 0
        assert "OCR results" in result.output or "hello" in result.output

    def test_ocr_languages(self):
        with patch("vector_studio.ocr_languages.get_tesseract_languages", return_value=[]):
            result = runner.invoke(app, ["ocr", "languages"])
        assert result.exit_code == 0
        assert "OCR Languages" in result.output or "Tesseract" in result.output


class TestResumeCommand:
    def test_resume_list_empty(self):
        result = runner.invoke(app, ["resume", "--list"])
        assert result.exit_code == 0

    def test_resume_no_checkpoint_id(self):
        result = runner.invoke(app, ["resume"])
        assert result.exit_code == 1
        assert "checkpoint_id is required" in result.output

    def test_resume_missing_checkpoint(self):
        result = runner.invoke(app, ["resume", "missing-cp"])
        assert result.exit_code == 1
        assert "No checkpoint found" in result.output


class TestMarketCommands:
    def test_market_list_empty(self):
        with patch("vector_studio.market.PresetMarket.discover_presets", return_value=[]):
            result = runner.invoke(app, ["market", "list"])
        assert result.exit_code == 0
        assert "No presets found" in result.output or "Market Presets" in result.output

    def test_market_search_empty(self):
        with patch("vector_studio.market.PresetMarket.search", return_value=[]):
            result = runner.invoke(app, ["market", "search", "logo"])
        assert result.exit_code == 0
        assert "No presets found" in result.output

    def test_market_popular_empty(self):
        with patch("vector_studio.market.PresetMarket.get_popular", return_value=[]):
            result = runner.invoke(app, ["market", "popular"])
        assert result.exit_code == 0
        assert "No popular presets" in result.output or "Popular Presets" in result.output

    def test_market_publish_no_token(self):
        with patch.dict(os.environ, {}, clear=True):
            result = runner.invoke(app, ["market", "publish", "my_preset"])
        assert result.exit_code == 1
        assert "GitHub token required" in result.output

    def test_market_info_failure(self):
        with patch("vector_studio.market.PresetMarket") as mock_market:
            mock_market.return_value.backend.download_preset.side_effect = RuntimeError("network error")
            result = runner.invoke(app, ["market", "info", "bad_id"])
        assert result.exit_code == 1
        assert "Failed to fetch" in result.output


class TestCloudCommands:
    def test_cloud_share(self, tmp_path):
        svg = tmp_path / "test.svg"
        svg.write_text("<svg></svg>")
        with patch("vector_studio.cli._get_cloud_manager") as mock_mgr:
            mock_mgr.return_value.share_svg.return_value = {
                "url": "http://localhost:8000/share/abc",
                "expire_at": "2025-01-01",
                "file_id": "abc",
                "qr_code": "base64data",
            }
            result = runner.invoke(app, ["cloud", "share", str(svg)])
        assert result.exit_code == 0
        assert "Shared" in result.output

    def test_cloud_list_empty(self):
        with patch("vector_studio.cli._get_cloud_manager") as mock_mgr:
            mock_mgr.return_value.get_shared_files.return_value = []
            result = runner.invoke(app, ["cloud", "list"])
        assert result.exit_code == 0
        assert "No active shares" in result.output

    def test_cloud_revoke(self):
        with patch("vector_studio.cli._get_cloud_manager") as mock_mgr:
            mock_mgr.return_value.revoke_share.return_value = True
            result = runner.invoke(app, ["cloud", "revoke", "abc"])
        assert result.exit_code == 0
        assert "Revoked" in result.output

    def test_cloud_revoke_not_found(self):
        with patch("vector_studio.cli._get_cloud_manager") as mock_mgr:
            mock_mgr.return_value.revoke_share.return_value = False
            result = runner.invoke(app, ["cloud", "revoke", "abc"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_cloud_qr(self):
        with patch("vector_studio.cli._get_cloud_manager") as mock_mgr:
            mock_mgr.return_value.backend.get_qr_code.return_value = b"pngdata"
            result = runner.invoke(app, ["cloud", "qr", "abc"])
        assert result.exit_code == 0


class TestContribCommand:
    def test_contrib_guide(self, tmp_path):
        output = tmp_path / "CONTRIBUTING.md"
        result = runner.invoke(app, ["contrib", "guide", "--output", str(output)])
        assert result.exit_code == 0
        assert output.exists()


class TestEngineCommands:
    def test_engine_list(self):
        with patch("vector_studio.engines.EngineRegistry.list_engines", return_value=[
            {"name": "vtracer", "version": "1.0", "available": True, "supported_formats": [".png"], "supported_outputs": [".svg"]},
        ]):
            result = runner.invoke(app, ["engine", "list"])
        assert result.exit_code == 0
        assert "vtracer" in result.output

    def test_engine_info(self):
        mock_engine = MagicMock()
        mock_engine.get_info.return_value = {
            "name": "vtracer", "version": "1.0", "available": True,
            "supported_formats": [".png"], "supported_outputs": [".svg"],
        }
        with patch("vector_studio.engines.EngineRegistry.get_engine", return_value=mock_engine):
            result = runner.invoke(app, ["engine", "info", "vtracer"])
        assert result.exit_code == 0
        assert "vtracer" in result.output

    def test_engine_info_missing(self):
        with patch("vector_studio.engines.EngineRegistry.get_engine", side_effect=ValueError("unknown")):
            result = runner.invoke(app, ["engine", "info", "bad_engine"])
        assert result.exit_code == 1
        assert "unknown" in result.output.lower() or "Error" in result.output

    def test_engine_benchmark(self, tmp_path):
        img = tmp_path / "img.png"
        img.write_bytes(b"fake")
        with patch("vector_studio.engines.EngineBenchmark.compare_engines", return_value=[
            {"engine": "vtracer", "elapsed_seconds": 0.5, "file_bytes": 100, "paths": 3, "quality_score": 80},
        ]):
            result = runner.invoke(app, ["engine", "benchmark", str(img)])
        assert result.exit_code == 0
        assert "vtracer" in result.output

    def test_engine_auto(self, tmp_path):
        img = tmp_path / "img.png"
        img.write_bytes(b"fake")
        mock_engine = MagicMock()
        mock_engine.get_info.return_value = {"name": "vtracer", "available": True}
        mock_result = TraceResult(
            input_path=img,
            svg_path=img.with_suffix(".svg"),
            engine="vtracer",
            elapsed_seconds=0.5,
            stats={"paths": 3},
        )
        with patch("vector_studio.engines.EngineRegistry.get_best_engine", return_value=mock_engine):
            with patch("vector_studio.cli.trace_image", return_value=mock_result):
                result = runner.invoke(app, ["engine", "auto", str(img)])
        assert result.exit_code == 0
        assert "vtracer" in result.output or "Done" in result.output
