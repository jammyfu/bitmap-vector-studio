from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from dataclasses import asdict
from pathlib import Path

from .ai_ocr import detect_text_regions, integrate_text_to_svg, recognize_text
from .ai_simplify import adaptive_simplify
from .models import TraceOptions, TraceResult
from .plugin_interface import Plugin
from .preprocess import prepare_input
from .svg_optimizer import optimize_svg_comprehensive
from .svg_tools import (
    export_svg_to_eps_with_inkscape,
    export_svg_to_pdf,
    export_svg_to_png,
    name_svg_layers,
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
    optimize_level: str = "basic",
    name_layers: bool = False,
    export_pdf: bool = False,
    export_png: bool = False,
    export_eps: bool = False,
    png_scale: float = 1.0,
    smart_remove_bg: bool = False,
    enhance: str | None = None,
    plugins: list[Plugin] | None = None,
    ai_simplify: bool = False,
    ai_ocr: bool = False,
    simplify_type: str = "auto",
    preview_mode: bool = False,
) -> TraceResult:
    """Convert a raster image to SVG using VTracer.

    The function first tries the official Python binding. If that package is not
    installed, it attempts to call a `vtracer` executable on PATH.

    Parameters
    ----------
    optimize_level:
        ``"none"`` skips post-processing.
        ``"basic"`` runs conservative cleanup.
        ``"comprehensive"`` runs deep optimization (path merge, color merge,
        path simplification).
        ``"aggressive"`` runs comprehensive with more aggressive thresholds.
    plugins:
        Optional list of :class:`~vector_studio.plugin_interface.Plugin`
        instances whose hooks will be executed during the pipeline.
    ai_simplify:
        If True, apply AI semantic simplification before tracing.
    ai_ocr:
        If True, detect and embed recognized text as editable SVG ``<text>``
        elements after tracing.
    simplify_type:
        Strategy for AI simplification: ``"photo"``, ``"complex"``, ``"sketch"``,
        or ``"auto"``.
    preview_mode:
        When ``True``, limits the input size to 400 px and skips PDF/PNG/EPS
        exports for a fast low-resolution preview.
    """
    start = time.perf_counter()
    input_path = Path(input_path)
    output_path = Path(output_path)
    options = (options or TraceOptions()).validate()
    plugins = plugins or []
    plugin_options: dict[str, object] = {
        "optimize": optimize,
        "optimize_level": optimize_level,
        "name_layers": name_layers,
        "export_pdf": export_pdf,
        "export_png": export_png,
        "export_eps": export_eps,
        "png_scale": png_scale,
        "smart_remove_bg": smart_remove_bg,
        "enhance": enhance,
        "ai_simplify": ai_simplify,
        "ai_ocr": ai_ocr,
        "simplify_type": simplify_type,
    }

    if preview_mode:
        opts_dict = asdict(options)
        current_max = opts_dict.get("max_input_side")
        if current_max is None or current_max > 400:
            opts_dict["max_input_side"] = 400
        options = TraceOptions(**opts_dict)
        export_pdf = False
        export_png = False
        export_eps = False

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
        prepare_input(input_path, normalized_input, options, smart_remove_bg=smart_remove_bg, enhance=enhance)

        # Run plugin preprocess hooks
        if plugins:
            from PIL import Image

            with Image.open(normalized_input) as img:
                for plugin in plugins:
                    try:
                        img = plugin.preprocess(img, plugin_options)
                    except Exception as exc:  # noqa: BLE001
                        import logging

                        logging.getLogger(__name__).warning(
                            "Plugin %s preprocess hook failed: %s", plugin.name, exc
                        )
                img.save(normalized_input, format="PNG", optimize=True)

        # AI semantic simplification (optional, non-blocking)
        if ai_simplify:
            try:
                from PIL import Image

                with Image.open(normalized_input) as img:
                    simplified = adaptive_simplify(img, image_type=simplify_type)
                    simplified.save(normalized_input, format="PNG", optimize=True)
            except Exception as exc:  # noqa: BLE001
                import logging

                logging.getLogger(__name__).warning("AI simplification failed: %s", exc)

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

    if optimize and optimize_level != "none":
        if optimize_level == "basic":
            optimize_svg_file(output_path)
        elif optimize_level in {"comprehensive", "aggressive"}:
            optimize_svg_comprehensive(output_path, aggressive=(optimize_level == "aggressive"))
        else:
            raise ValueError(
                "optimize_level must be one of: none, basic, comprehensive, aggressive."
            )

    if name_layers:
        name_svg_layers(output_path)

    # AI OCR text integration (optional, non-blocking)
    if ai_ocr:
        try:
            from PIL import Image

            with Image.open(input_path) as img:
                regions = recognize_text(img)
                if regions:
                    integrate_text_to_svg(output_path, regions, output_path)
        except Exception as exc:  # noqa: BLE001
            import logging

            logging.getLogger(__name__).warning("AI OCR failed: %s", exc)

    # Run plugin postprocess hooks
    for plugin in plugins:
        try:
            output_path = plugin.postprocess(output_path, plugin_options)
        except Exception as exc:  # noqa: BLE001
            import logging

            logging.getLogger(__name__).warning(
                "Plugin %s postprocess hook failed: %s", plugin.name, exc
            )

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
    result = TraceResult(
        input_path=input_path,
        svg_path=output_path,
        engine=engine,
        elapsed_seconds=elapsed,
        stats=svg_stats(output_path),
        pdf_path=pdf_path,
        png_path=png_path,
        eps_path=eps_path,
    )

    # Run plugin on_complete hooks
    for plugin in plugins:
        try:
            plugin.on_convert_complete(result, plugin_options)
        except Exception as exc:  # noqa: BLE001
            import logging

            logging.getLogger(__name__).warning(
                "Plugin %s on_complete hook failed: %s", plugin.name, exc
            )

    return result
