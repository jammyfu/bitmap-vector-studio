from dataclasses import replace
from pathlib import Path

import pytest

from vector_studio.models import TraceOptions, TraceResult


class TestTraceOptionsDefaults:
    def test_default_values(self):
        opts = TraceOptions()
        assert opts.colormode == "color"
        assert opts.hierarchical == "stacked"
        assert opts.mode == "spline"
        assert opts.filter_speckle == 4
        assert opts.color_precision == 6
        assert opts.layer_difference == 16
        assert opts.corner_threshold == 60
        assert opts.length_threshold == 4.0
        assert opts.max_iterations == 10
        assert opts.splice_threshold == 45
        assert opts.path_precision == 3
        assert opts.denoise is False
        assert opts.posterize is None
        assert opts.max_input_side is None
        assert opts.alpha_background == "#ffffff"


class TestTraceOptionsValidate:
    def test_valid_defaults_pass(self):
        opts = TraceOptions()
        assert opts.validate() is opts

    def test_valid_boundary_values(self):
        assert TraceOptions(filter_speckle=0).validate()
        assert TraceOptions(filter_speckle=128).validate()
        assert TraceOptions(color_precision=1).validate()
        assert TraceOptions(color_precision=8).validate()
        assert TraceOptions(layer_difference=0).validate()
        assert TraceOptions(layer_difference=255).validate()
        assert TraceOptions(corner_threshold=0).validate()
        assert TraceOptions(corner_threshold=180).validate()
        assert TraceOptions(length_threshold=3.5).validate()
        assert TraceOptions(length_threshold=10.0).validate()
        assert TraceOptions(max_iterations=1).validate()
        assert TraceOptions(max_iterations=50).validate()
        assert TraceOptions(splice_threshold=0).validate()
        assert TraceOptions(splice_threshold=180).validate()
        assert TraceOptions(path_precision=0).validate()
        assert TraceOptions(path_precision=12).validate()
        assert TraceOptions(posterize=1).validate()
        assert TraceOptions(posterize=8).validate()
        assert TraceOptions(max_input_side=64).validate()
        assert TraceOptions(max_input_side=1024).validate()

    def test_invalid_colormode(self):
        with pytest.raises(ValueError, match="colormode must be"):
            TraceOptions(colormode="grayscale").validate()

    def test_invalid_hierarchical(self):
        with pytest.raises(ValueError, match="hierarchical must be"):
            TraceOptions(hierarchical="flat").validate()

    def test_invalid_mode(self):
        with pytest.raises(ValueError, match="mode must be"):
            TraceOptions(mode="bezier").validate()

    def test_invalid_filter_speckle_negative(self):
        with pytest.raises(ValueError, match="filter_speckle must be between"):
            TraceOptions(filter_speckle=-1).validate()

    def test_invalid_filter_speckle_too_high(self):
        with pytest.raises(ValueError, match="filter_speckle must be between"):
            TraceOptions(filter_speckle=129).validate()

    def test_invalid_color_precision_zero(self):
        with pytest.raises(ValueError, match="color_precision must be between"):
            TraceOptions(color_precision=0).validate()

    def test_invalid_color_precision_too_high(self):
        with pytest.raises(ValueError, match="color_precision must be between"):
            TraceOptions(color_precision=9).validate()

    def test_invalid_layer_difference_negative(self):
        with pytest.raises(ValueError, match="layer_difference must be between"):
            TraceOptions(layer_difference=-1).validate()

    def test_invalid_layer_difference_too_high(self):
        with pytest.raises(ValueError, match="layer_difference must be between"):
            TraceOptions(layer_difference=256).validate()

    def test_invalid_corner_threshold(self):
        with pytest.raises(ValueError, match="corner_threshold must be between"):
            TraceOptions(corner_threshold=181).validate()

    def test_invalid_length_threshold_low(self):
        with pytest.raises(ValueError, match="length_threshold must be between"):
            TraceOptions(length_threshold=3.4).validate()

    def test_invalid_length_threshold_high(self):
        with pytest.raises(ValueError, match="length_threshold must be between"):
            TraceOptions(length_threshold=10.1).validate()

    def test_invalid_max_iterations_zero(self):
        with pytest.raises(ValueError, match="max_iterations must be between"):
            TraceOptions(max_iterations=0).validate()

    def test_invalid_max_iterations_too_high(self):
        with pytest.raises(ValueError, match="max_iterations must be between"):
            TraceOptions(max_iterations=51).validate()

    def test_invalid_splice_threshold(self):
        with pytest.raises(ValueError, match="splice_threshold must be between"):
            TraceOptions(splice_threshold=181).validate()

    def test_invalid_path_precision_negative(self):
        with pytest.raises(ValueError, match="path_precision must be between"):
            TraceOptions(path_precision=-1).validate()

    def test_invalid_path_precision_too_high(self):
        with pytest.raises(ValueError, match="path_precision must be between"):
            TraceOptions(path_precision=13).validate()

    def test_invalid_posterize_zero(self):
        with pytest.raises(ValueError, match="posterize must be None or between"):
            TraceOptions(posterize=0).validate()

    def test_invalid_posterize_too_high(self):
        with pytest.raises(ValueError, match="posterize must be None or between"):
            TraceOptions(posterize=9).validate()

    def test_invalid_max_input_side_too_small(self):
        with pytest.raises(ValueError, match="max_input_side must be None or at least"):
            TraceOptions(max_input_side=63).validate()


class TestTraceOptionsVtracerKwargs:
    def test_vtracer_kwargs_structure(self, sample_trace_options):
        kwargs = sample_trace_options.vtracer_kwargs()
        assert isinstance(kwargs, dict)
        assert kwargs["colormode"] == "color"
        assert kwargs["hierarchical"] == "stacked"
        assert kwargs["mode"] == "spline"
        assert kwargs["filter_speckle"] == 4
        assert kwargs["color_precision"] == 6
        assert kwargs["layer_difference"] == 16
        assert kwargs["corner_threshold"] == 60
        assert kwargs["length_threshold"] == 4.0
        assert kwargs["max_iterations"] == 10
        assert kwargs["splice_threshold"] == 45
        assert kwargs["path_precision"] == 3

    def test_vtracer_kwargs_excludes_local_options(self, sample_trace_options):
        kwargs = sample_trace_options.vtracer_kwargs()
        assert "denoise" not in kwargs
        assert "posterize" not in kwargs
        assert "max_input_side" not in kwargs
        assert "alpha_background" not in kwargs

    def test_vtracer_kwargs_validates_first(self):
        bad = TraceOptions(colormode="invalid")
        with pytest.raises(ValueError):
            bad.vtracer_kwargs()

    def test_vtracer_kwargs_types(self):
        opts = TraceOptions(
            filter_speckle=4.0,
            color_precision=6.0,
            layer_difference=16.0,
            corner_threshold=60.0,
            max_iterations=10.0,
            splice_threshold=45.0,
            path_precision=3.0,
        )
        kwargs = opts.vtracer_kwargs()
        assert isinstance(kwargs["filter_speckle"], int)
        assert isinstance(kwargs["color_precision"], int)
        assert isinstance(kwargs["layer_difference"], int)
        assert isinstance(kwargs["corner_threshold"], int)
        assert isinstance(kwargs["length_threshold"], float)
        assert isinstance(kwargs["max_iterations"], int)
        assert isinstance(kwargs["splice_threshold"], int)
        assert isinstance(kwargs["path_precision"], int)


class TestTraceOptionsVtracerCliArgs:
    def test_cli_args_structure(self, sample_trace_options, tmp_path):
        input_path = tmp_path / "in.png"
        output_path = tmp_path / "out.svg"
        args = sample_trace_options.vtracer_cli_args(input_path, output_path)
        assert isinstance(args, list)
        assert args == [
            "--input", str(input_path),
            "--output", str(output_path),
            "--colormode", "color",
            "--hierarchical", "stacked",
            "--mode", "spline",
            "--filter_speckle", "4",
            "--color_precision", "6",
            "--gradient_step", "16",
            "--corner_threshold", "60",
            "--segment_length", "4.0",
            "--splice_threshold", "45",
            "--path_precision", "3",
        ]

    def test_cli_args_binary_colormode_maps_to_bw(self, tmp_path):
        opts = TraceOptions(colormode="binary")
        args = opts.vtracer_cli_args(tmp_path / "in.png", tmp_path / "out.svg")
        assert "--colormode" in args
        idx = args.index("--colormode")
        assert args[idx + 1] == "bw"

    def test_cli_args_layer_difference_maps_to_gradient_step(self, tmp_path):
        opts = TraceOptions(layer_difference=32)
        args = opts.vtracer_cli_args(tmp_path / "in.png", tmp_path / "out.svg")
        assert "--gradient_step" in args
        idx = args.index("--gradient_step")
        assert args[idx + 1] == "32"

    def test_cli_args_validates_first(self, tmp_path):
        bad = TraceOptions(colormode="invalid")
        with pytest.raises(ValueError):
            bad.vtracer_cli_args(tmp_path / "in.png", tmp_path / "out.svg")


class TestTraceOptionsImmutability:
    def test_frozen_dataclass_cannot_mutate(self):
        opts = TraceOptions()
        with pytest.raises(AttributeError, match="cannot assign to field"):
            opts.colormode = "binary"

    def test_replace_creates_new_instance(self):
        opts = TraceOptions()
        new_opts = replace(opts, colormode="binary")
        assert new_opts.colormode == "binary"
        assert opts.colormode == "color"

    def test_replace_preserves_untouched_fields(self):
        opts = TraceOptions(filter_speckle=8)
        new_opts = replace(opts, colormode="binary")
        assert new_opts.filter_speckle == 8
        assert new_opts.colormode == "binary"


class TestTraceResult:
    def test_trace_result_defaults(self, tmp_path):
        result = TraceResult(
            input_path=tmp_path / "in.png",
            svg_path=tmp_path / "out.svg",
            engine="python-vtracer",
            elapsed_seconds=1.23,
        )
        assert result.stats == {}
        assert result.pdf_path is None
        assert result.png_path is None
        assert result.eps_path is None

    def test_trace_result_with_all_exports(self, tmp_path):
        result = TraceResult(
            input_path=tmp_path / "in.png",
            svg_path=tmp_path / "out.svg",
            engine="python-vtracer",
            elapsed_seconds=2.0,
            stats={"paths": 5},
            pdf_path=tmp_path / "out.pdf",
            png_path=tmp_path / "out.png",
            eps_path=tmp_path / "out.eps",
        )
        assert result.stats["paths"] == 5
        assert result.pdf_path == tmp_path / "out.pdf"
        assert result.png_path == tmp_path / "out.png"
        assert result.eps_path == tmp_path / "out.eps"

    def test_trace_result_frozen(self, tmp_path):
        result = TraceResult(
            input_path=tmp_path / "in.png",
            svg_path=tmp_path / "out.svg",
            engine="python-vtracer",
            elapsed_seconds=1.0,
        )
        with pytest.raises(AttributeError, match="cannot assign to field"):
            result.engine = "vtracer-cli"
