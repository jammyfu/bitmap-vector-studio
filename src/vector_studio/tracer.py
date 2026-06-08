from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
import time
from dataclasses import asdict
from pathlib import Path

from .ai_ocr import detect_text_regions, integrate_text_to_svg, recognize_text, recognize_text_multilang
from .ai_simplify import adaptive_simplify
from .models import TraceOptions, TraceResult
from .plugin_interface import Plugin
from .performance import PerformanceMonitor, StreamingImageProcessor
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
from .ai_onnx import AIProcessor
from .engines import EngineRegistry, VTracerEngine
from .gpu_backend import detect_gpu, gpu_preprocess, GPUBackend

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
    engine: str = "vtracer",
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
    ocr_lang: str | None = None,
    simplify_type: str = "auto",
    preview_mode: bool = False,
    use_gpu: bool = False,
    stream: bool = False,
    ai_pipeline: list[str] | None = None,
) -> TraceResult:
    """Convert a raster image to SVG using the specified vectorization engine.

    The function first tries the official Python binding. If that package is not
    installed, it attempts to call a `vtracer` executable on PATH.

    Parameters
    ----------
    engine:
        Vectorization engine to use.  ``"vtracer"`` (default), ``"potrace"``,
        or ``"autotrace"``.  If the requested engine is unavailable the call
        falls back to VTracer automatically.
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
    ocr_lang:
        Optional OCR language code (e.g. ``"chi_sim"``, ``"jpn"``). When
        ``ai_ocr`` is enabled, this language is passed to the OCR engine.
    simplify_type:
        Strategy for AI simplification: ``"photo"``, ``"complex"``, ``"sketch"``,
        or ``"auto"``.
    preview_mode:
        When ``True``, limits the input size to 400 px and skips PDF/PNG/EPS
        exports for a fast low-resolution preview.
    use_gpu:
        When ``True``, attempt GPU-accelerated preprocessing. Falls back to CPU
        if no GPU is available or the operation fails.
    stream:
        When ``True``, force chunked/streaming processing for large images.
    ai_pipeline:
        Optional list of AI pre-processing task names executed before
        tracing.  Supported values: ``"segment"``, ``"style_transfer"``,
        ``"upscale"``, ``"auto_enhance"``.  Each task is run in order via
        :class:`~vector_studio.ai_onnx.AIProcessor`.
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
        "ocr_lang": ocr_lang,
        "simplify_type": simplify_type,
        "use_gpu": use_gpu,
        "stream": stream,
        "ai_pipeline": ai_pipeline,
    }

    # Performance monitoring hook
    perf_monitor = PerformanceMonitor()
    perf_suggestions = perf_monitor.suggest_optimization(input_path)
    if perf_suggestions:
        logger = logging.getLogger(__name__)
        logger.debug("Performance suggestions: %s", perf_suggestions)

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

    # Auto-detect large images and use streaming processor
    if stream or StreamingImageProcessor._should_stream(input_path):
        processor = StreamingImageProcessor()
        svg_path = processor.process_large_image(input_path, output_path, options)
        # Build a minimal TraceResult for the streaming path
        elapsed = time.perf_counter() - start
        result = TraceResult(
            input_path=input_path,
            svg_path=svg_path,
            engine="streaming-vtracer",
            elapsed_seconds=elapsed,
            stats=svg_stats(svg_path),
        )
        # Post-processing for streaming result
        if optimize and optimize_level != "none":
            if optimize_level == "basic":
                optimize_svg_file(svg_path)
            elif optimize_level in {"comprehensive", "aggressive"}:
                optimize_svg_comprehensive(svg_path, aggressive=(optimize_level == "aggressive"))
        if name_layers:
            name_svg_layers(svg_path)
        if export_pdf:
            pdf_path = export_svg_to_pdf(svg_path, svg_path.with_suffix(".pdf"))
            result = TraceResult(
                input_path=input_path,
                svg_path=svg_path,
                engine=result.engine,
                elapsed_seconds=result.elapsed_seconds,
                stats=result.stats,
                pdf_path=pdf_path,
            )
        if export_png:
            png_path = export_svg_to_png(svg_path, svg_path.with_suffix(".png"), scale=png_scale)
            result = TraceResult(
                input_path=input_path,
                svg_path=svg_path,
                engine=result.engine,
                elapsed_seconds=result.elapsed_seconds,
                stats=result.stats,
                pdf_path=result.pdf_path,
                png_path=png_path,
            )
        if export_eps:
            eps_path = export_svg_to_eps_with_inkscape(svg_path, svg_path.with_suffix(".eps"))
            result = TraceResult(
                input_path=input_path,
                svg_path=svg_path,
                engine=result.engine,
                elapsed_seconds=result.elapsed_seconds,
                stats=result.stats,
                pdf_path=result.pdf_path,
                png_path=result.png_path,
                eps_path=eps_path,
            )
        return result

    # Determine engine
    registry = EngineRegistry()
    requested = engine.strip().lower()
    try:
        engine_instance = registry.get_engine(requested)
        if not engine_instance.is_available():
            logger = logging.getLogger(__name__)
            logger.warning("Engine '%s' is not available, falling back to vtracer.", requested)
            engine_instance = VTracerEngine()
            requested = "vtracer"
    except ValueError:
        logger = logging.getLogger(__name__)
        logger.warning("Unknown engine '%s', falling back to vtracer.", requested)
        engine_instance = VTracerEngine()
        requested = "vtracer"

    engine_label = requested
    with tempfile.TemporaryDirectory(prefix="vector-studio-") as tmp:
        normalized_input = Path(tmp) / "input.png"
        prepare_input(input_path, normalized_input, options, smart_remove_bg=smart_remove_bg, enhance=enhance)

        # AI pipeline preprocessing (optional)
        if ai_pipeline:
            try:
                from PIL import Image

                ai_processor = AIProcessor()
                with Image.open(normalized_input) as img:
                    for task in ai_pipeline:
                        task_lower = task.strip().lower()
                        if task_lower == "segment":
                            img = ai_processor.process(img, "segment")
                        elif task_lower == "style_transfer":
                            style = "sketch"
                            img = ai_processor.process(img, "style_transfer", style=style)
                        elif task_lower == "upscale":
                            img = ai_processor.process(img, "upscale", scale=2)
                        elif task_lower == "auto_enhance":
                            img = ai_processor.process(img, "auto_enhance", scale=2)
                        else:
                            logger = logging.getLogger(__name__)
                            logger.warning("Unknown ai_pipeline task '%s', skipping.", task)
                    img.save(normalized_input, format="PNG", optimize=True)
            except Exception as exc:  # noqa: BLE001
                logger = logging.getLogger(__name__)
                logger.warning("AI pipeline failed: %s", exc)

        # GPU-accelerated preprocessing (optional)
        if use_gpu:
            try:
                from PIL import Image

                backend = detect_gpu()
                if backend != GPUBackend.NONE:
                    with Image.open(normalized_input) as img:
                        processed = gpu_preprocess(img, backend=backend)
                        processed.save(normalized_input, format="PNG", optimize=True)
            except Exception as exc:
                logger = logging.getLogger(__name__)
                logger.warning("GPU preprocessing failed, falling back to CPU: %s", exc)

        # Run plugin preprocess hooks
        if plugins:
            from PIL import Image

            with Image.open(normalized_input) as img:
                for plugin in plugins:
                    try:
                        img = plugin.preprocess(img, plugin_options)
                    except Exception as exc:  # noqa: BLE001
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
                logging.getLogger(__name__).warning("AI simplification failed: %s", exc)

        if requested == "vtracer":
            try:
                _trace_with_python_binding(normalized_input, output_path, options)
                engine_label = "python-vtracer"
            except Exception as python_error:
                engine_label = "vtracer-cli"
                try:
                    _trace_with_cli(normalized_input, output_path, options)
                except Exception as cli_error:
                    raise RuntimeError(
                        "VTracer conversion failed. Install the Python package with "
                        "`pip install vtracer`, or install the VTracer CLI. "
                        f"Python binding error: {python_error}. CLI error: {cli_error}."
                    ) from cli_error
        else:
            engine_options: dict[str, object] = {"trace_options": options}
            if requested == "potrace":
                engine_options.update({
                    k: v for k, v in {
                        "turdsize": getattr(options, "filter_speckle", None),
                        "alphamax": getattr(options, "corner_threshold", None),
                        "opticurve": True,
                    }.items() if v is not None
                })
            elif requested == "autotrace":
                engine_options.update({
                    k: v for k, v in {
                        "color_count": getattr(options, "color_precision", None),
                        "despeckle_level": getattr(options, "filter_speckle", None),
                        "corner_threshold": getattr(options, "corner_threshold", None),
                    }.items() if v is not None
                })
            engine_instance.convert(normalized_input, output_path, engine_options)
            engine_label = requested

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
                regions = recognize_text_multilang(img, lang=ocr_lang)
                if regions:
                    integrate_text_to_svg(output_path, regions, output_path)
        except Exception as exc:  # noqa: BLE001
            logging.getLogger(__name__).warning("AI OCR failed: %s", exc)

    # Run plugin postprocess hooks
    for plugin in plugins:
        try:
            output_path = plugin.postprocess(output_path, plugin_options)
        except Exception as exc:  # noqa: BLE001
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
        engine=engine_label,
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
            logging.getLogger(__name__).warning(
                "Plugin %s on_complete hook failed: %s", plugin.name, exc
            )

    return result
