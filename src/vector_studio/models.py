from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

ColorMode = Literal["color", "binary"]
HierarchicalMode = Literal["stacked", "cutout"]
CurveMode = Literal["spline", "polygon", "pixel", "none"]


@dataclass(frozen=True)
class TraceOptions:
    """Options passed to VTracer plus lightweight local preprocessing flags.

    Values are intentionally close to the official VTracer Python API so the
    wrapper remains easy to maintain when VTracer updates.
    """

    colormode: ColorMode = "color"
    hierarchical: HierarchicalMode = "stacked"
    mode: CurveMode = "spline"
    filter_speckle: int = 4
    color_precision: int = 6
    layer_difference: int = 16
    corner_threshold: int = 60
    length_threshold: float = 4.0
    max_iterations: int = 10
    splice_threshold: int = 45
    path_precision: int = 3

    # Local preprocessing controls. These are not VTracer parameters.
    denoise: bool = False
    posterize: int | None = None
    max_input_side: int | None = None
    alpha_background: str | None = "#ffffff"

    def validate(self) -> "TraceOptions":
        if self.colormode not in {"color", "binary"}:
            raise ValueError("colormode must be 'color' or 'binary'.")
        if self.hierarchical not in {"stacked", "cutout"}:
            raise ValueError("hierarchical must be 'stacked' or 'cutout'.")
        if self.mode not in {"spline", "polygon", "pixel", "none"}:
            raise ValueError("mode must be 'spline', 'polygon', 'pixel', or 'none'.")
        if not 0 <= self.filter_speckle <= 128:
            raise ValueError("filter_speckle must be between 0 and 128.")
        if not 1 <= self.color_precision <= 8:
            raise ValueError("color_precision must be between 1 and 8.")
        if not 0 <= self.layer_difference <= 255:
            raise ValueError("layer_difference must be between 0 and 255.")
        if not 0 <= self.corner_threshold <= 180:
            raise ValueError("corner_threshold must be between 0 and 180.")
        if not 3.5 <= float(self.length_threshold) <= 10.0:
            raise ValueError("length_threshold must be between 3.5 and 10.0.")
        if not 1 <= self.max_iterations <= 50:
            raise ValueError("max_iterations must be between 1 and 50.")
        if not 0 <= self.splice_threshold <= 180:
            raise ValueError("splice_threshold must be between 0 and 180.")
        if not 0 <= self.path_precision <= 12:
            raise ValueError("path_precision must be between 0 and 12.")
        if self.posterize is not None and not 1 <= int(self.posterize) <= 8:
            raise ValueError("posterize must be None or between 1 and 8 bits.")
        if self.max_input_side is not None and int(self.max_input_side) < 64:
            raise ValueError("max_input_side must be None or at least 64 pixels.")
        return self

    def vtracer_kwargs(self) -> dict[str, Any]:
        """Keyword arguments for vtracer.convert_image_to_svg_py."""
        self.validate()
        return {
            "colormode": self.colormode,
            "hierarchical": self.hierarchical,
            "mode": self.mode,
            "filter_speckle": int(self.filter_speckle),
            "color_precision": int(self.color_precision),
            "layer_difference": int(self.layer_difference),
            "corner_threshold": int(self.corner_threshold),
            "length_threshold": float(self.length_threshold),
            "max_iterations": int(self.max_iterations),
            "splice_threshold": int(self.splice_threshold),
            "path_precision": int(self.path_precision),
        }

    def vtracer_cli_args(self, input_path: Path, output_path: Path) -> list[str]:
        """Arguments for the optional VTracer CLI fallback.

        Older command-line docs use `bw` for binary mode and `gradient_step` for
        what the Python API calls `layer_difference`, so the wrapper maps names.
        """
        self.validate()
        cli_colormode = "bw" if self.colormode == "binary" else "color"
        return [
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--colormode",
            cli_colormode,
            "--hierarchical",
            self.hierarchical,
            "--mode",
            self.mode,
            "--filter_speckle",
            str(int(self.filter_speckle)),
            "--color_precision",
            str(int(self.color_precision)),
            "--gradient_step",
            str(int(self.layer_difference)),
            "--corner_threshold",
            str(int(self.corner_threshold)),
            "--segment_length",
            str(float(self.length_threshold)),
            "--splice_threshold",
            str(int(self.splice_threshold)),
            "--path_precision",
            str(int(self.path_precision)),
        ]


@dataclass(frozen=True)
class TraceResult:
    input_path: Path
    svg_path: Path
    engine: str
    elapsed_seconds: float
    stats: dict[str, Any] = field(default_factory=dict)
    pdf_path: Path | None = None
    png_path: Path | None = None
    eps_path: Path | None = None
