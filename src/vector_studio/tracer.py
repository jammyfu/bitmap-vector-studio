from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from .models import TraceOptions, TraceResult
from .preprocess import prepare_input
from .svg_tools import (
    export_svg_to_eps_with_inkscape,
    export_svg_to_pdf,
    export_svg_to_png,
    optimize_svg_file,
    svg_stats,
)

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


def _trace_with_python_binding(input_path: Path, output_path: Path, options: TraceOptions) -> None:
    try:
        import vtracer
    except ImportError as exc:
        raise RuntimeError("Python package 'vtracer' is not installed.") from exc

    vtracer.convert_image_to_svg_py(str(input_path), str(output_path), **options.vtracer_kwargs())


def _trace_with_cli(input_path: Path, output_path: Path, options: TraceOptions) -> None:
    executable = shutil.which("vtracer")
    if not executable:
        raise RuntimeError("VTracer CLI was not found on PATH.")

    command = [executable, *options.vtracer_cli_args(input_path, output_path)]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "VTracer CLI failed.")


def trace_image(
    input_path: Path | str,
    output_path: Path | str,
    options: TraceOptions | None = None,
    *,
    optimize: bool = True,
    export_pdf: bool = False,
    export_png: bool = False,
    export_eps: bool = False,
    png_scale: float = 1.0,
) -> TraceResult:
    """Convert a raster image to SVG using VTracer.

    The function first tries the official Python binding. If that package is not
    installed, it attempts to call a `vtracer` executable on PATH.
    """
    start = time.perf_counter()
    input_path = Path(input_path)
    output_path = Path(output_path)
    options = (options or TraceOptions()).validate()

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    if input_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        valid = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Unsupported input format: {input_path.suffix}. Supported: {valid}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() != ".svg":
        output_path = output_path.with_suffix(".svg")

    engine = "python-vtracer"
    with tempfile.TemporaryDirectory(prefix="vector-studio-") as tmp:
        normalized_input = Path(tmp) / "input.png"
        prepare_input(input_path, normalized_input, options)

        try:
            _trace_with_python_binding(normalized_input, output_path, options)
        except Exception as python_error:
            engine = "vtracer-cli"
            try:
                _trace_with_cli(normalized_input, output_path, options)
            except Exception as cli_error:
                raise RuntimeError(
                    "VTracer conversion failed. Install the Python package with "
                    "`pip install vtracer`, or install the VTracer CLI. "
                    f"Python binding error: {python_error}. CLI error: {cli_error}."
                ) from cli_error

    if optimize:
        optimize_svg_file(output_path)

    pdf_path = None
    png_path = None
    eps_path = None
    if export_pdf:
        pdf_path = export_svg_to_pdf(output_path, output_path.with_suffix(".pdf"))
    if export_png:
        png_path = export_svg_to_png(output_path, output_path.with_suffix(".png"), scale=png_scale)
    if export_eps:
        eps_path = export_svg_to_eps_with_inkscape(output_path, output_path.with_suffix(".eps"))

    elapsed = time.perf_counter() - start
    return TraceResult(
        input_path=input_path,
        svg_path=output_path,
        engine=engine,
        elapsed_seconds=elapsed,
        stats=svg_stats(output_path),
        pdf_path=pdf_path,
        png_path=png_path,
        eps_path=eps_path,
    )
