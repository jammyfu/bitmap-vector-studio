from __future__ import annotations

import logging
import tempfile
import time
from pathlib import Path
from typing import Any

from PIL import Image, ImageStat

from .ai_onnx import AIProcessor
from .engines import EngineRegistry, VTracerEngine
from .models import TraceOptions, TraceResult
from .tracer import trace_image

logger = logging.getLogger(__name__)


class EngineOrchestrator:
    """Analyse images and recommend / execute multi-step processing pipelines."""

    def __init__(self) -> None:
        """Initialize the orchestrator with a fresh engine registry."""
        self.registry = EngineRegistry()
        self.ai = AIProcessor()

    def analyze_image(self, image_path: Path) -> dict[str, Any]:
        """Analyse visual characteristics of *image_path*.

        Parameters
        ----------
        image_path:
            Path to a bitmap image.

        Returns
        -------
        dict
            Keys include ``image_type``, ``complexity``, ``color_count``,
            ``edge_density``, ``aspect_ratio``, ``is_likely_logo``,
            ``is_likely_photo``, ``is_likely_scan``.
        """
        with Image.open(image_path) as img:
            mode = img.mode
            width, height = img.size
            aspect_ratio = round(width / height, 3) if height else 0.0

            # Convert to RGB for analysis
            rgb = img.convert("RGB")
            stat = ImageStat.Stat(rgb)
            stddev = sum(stat.stddev) / 3.0 if stat.stddev else 0.0

            # Palette-based colour count proxy
            palette = rgb.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
            color_count = len({c for c in palette.getdata()})

            # Edge density proxy: convert to greyscale and measure stddev
            gray = rgb.convert("L")
            edge_std = ImageStat.Stat(gray).stddev[0] if ImageStat.Stat(gray).stddev else 0.0
            edge_density = round(edge_std / 255.0, 3)

            # Heuristics
            is_likely_logo = (
                (mode in ("1", "P", "L") and width < 512 and height < 512)
                or (mode == "RGBA" and color_count < 16 and width < 1024 and height < 1024)
                or (width < 256 and height < 256 and color_count < 8)
            )
            is_likely_photo = color_count > 64 and stddev > 20 and width * height > 300_000
            is_likely_scan = stddev < 40 and edge_density < 0.2 and color_count < 48 and width * height > 100_000

            # Complexity score (0-100)
            complexity = min(100, int(color_count / 2 + edge_density * 100))

            image_type = "unknown"
            if is_likely_scan:
                image_type = "scan"
            elif is_likely_photo:
                image_type = "photo"
            elif is_likely_logo:
                image_type = "logo"
            else:
                image_type = "complex"

        return {
            "image_type": image_type,
            "complexity": complexity,
            "color_count": color_count,
            "edge_density": edge_density,
            "aspect_ratio": aspect_ratio,
            "is_likely_logo": is_likely_logo,
            "is_likely_photo": is_likely_photo,
            "is_likely_scan": is_likely_scan,
            "width": width,
            "height": height,
        }

    def recommend_pipeline(self, image_path: Path) -> list[dict[str, Any]]:
        """Recommend an AI + engine pipeline for *image_path*.

        Rules:
        * Photo  → upscale → style_transfer (sketch) → VTracer
        * Logo   → segment → Potrace
        * Scan   → auto_enhance → VTracer
        * Other  → VTracer (no AI pre-processing)

        Parameters
        ----------
        image_path:
            Path to a bitmap image.

        Returns
        -------
        list[dict]
            Ordered list of pipeline steps.  Each dict has ``step``,
            ``task``, ``engine``, and optional ``kwargs``.
        """
        analysis = self.analyze_image(image_path)
        image_type = analysis["image_type"]
        pipeline: list[dict[str, Any]] = []

        if image_type == "photo":
            pipeline.append({
                "step": "ai_upscale",
                "task": "upscale",
                "kwargs": {"scale": 2},
            })
            pipeline.append({
                "step": "ai_style",
                "task": "style_transfer",
                "kwargs": {"style": "sketch"},
            })
            pipeline.append({
                "step": "vectorize",
                "engine": "vtracer",
                "kwargs": {},
            })
        elif image_type == "logo":
            pipeline.append({
                "step": "ai_segment",
                "task": "segment",
                "kwargs": {},
            })
            pipeline.append({
                "step": "vectorize",
                "engine": "potrace",
                "kwargs": {},
            })
        elif image_type == "scan":
            pipeline.append({
                "step": "ai_enhance",
                "task": "auto_enhance",
                "kwargs": {"scale": 2},
            })
            pipeline.append({
                "step": "vectorize",
                "engine": "vtracer",
                "kwargs": {},
            })
        else:
            pipeline.append({
                "step": "vectorize",
                "engine": "vtracer",
                "kwargs": {},
            })

        return pipeline

    def run_pipeline(
        self,
        image_path: Path,
        pipeline: list[dict[str, Any]],
        output_path: Path,
        trace_options: TraceOptions | None = None,
    ) -> TraceResult:
        """Execute a processing *pipeline* and return a :class:`TraceResult`.

        Parameters
        ----------
        image_path:
            Original bitmap.
        pipeline:
            List of step dicts as returned by :meth:`recommend_pipeline`.
        output_path:
            Final SVG destination.
        trace_options:
            Optional :class:`TraceOptions` for the vectorization step.

        Returns
        -------
        TraceResult
        """
        start = time.perf_counter()
        current_image = Image.open(image_path)
        current_path = image_path
        engine = "vtracer"

        with tempfile.TemporaryDirectory(prefix="vs-orchestrator-") as tmp:
            tmp_path = Path(tmp)

            for step in pipeline:
                step_name = step.get("step", "unknown")

                if step_name.startswith("ai_"):
                    task = step.get("task")
                    kwargs = step.get("kwargs", {})
                    try:
                        current_image = self.ai.process(current_image, task, **kwargs)
                        # Save to temp file for next step / final trace
                        step_file = tmp_path / f"{step_name}.png"
                        if current_image.mode in ("P", "RGBA", "L", "1"):
                            current_image.save(step_file, format="PNG", optimize=True)
                        else:
                            current_image.convert("RGB").save(step_file, format="PNG", optimize=True)
                        current_path = step_file
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("Pipeline step '%s' failed: %s", step_name, exc)
                        # Continue with the previous image

                elif step_name == "vectorize":
                    engine = step.get("engine", "vtracer")
                    trace_opts = trace_options or TraceOptions()
                    # If the last AI step produced an image, save it
                    if current_path != image_path:
                        current_path = tmp_path / "preprocessed.png"
                        if current_image.mode in ("P", "RGBA", "L", "1"):
                            current_image.save(current_path, format="PNG", optimize=True)
                        else:
                            current_image.convert("RGB").save(current_path, format="PNG", optimize=True)

                    result = trace_image(
                        current_path,
                        output_path,
                        trace_opts,
                        engine=engine,
                    )
                    elapsed = time.perf_counter() - start
                    # Rebuild result with the original input path and total time
                    return TraceResult(
                        input_path=image_path,
                        svg_path=result.svg_path,
                        engine=f"orchestrator:{engine}",
                        elapsed_seconds=elapsed,
                        stats=result.stats,
                        pdf_path=result.pdf_path,
                        png_path=result.png_path,
                        eps_path=result.eps_path,
                    )

        # If the pipeline had no vectorize step, run a default trace
        result = trace_image(
            current_path,
            output_path,
            trace_options or TraceOptions(),
            engine=engine,
        )
        elapsed = time.perf_counter() - start
        return TraceResult(
            input_path=image_path,
            svg_path=result.svg_path,
            engine=f"orchestrator:{engine}",
            elapsed_seconds=elapsed,
            stats=result.stats,
            pdf_path=result.pdf_path,
            png_path=result.png_path,
            eps_path=result.eps_path,
        )
