from __future__ import annotations

import importlib
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .models import TraceOptions

logger = logging.getLogger(__name__)


class _GPUBackend(Enum):
    """Internal GPU backend enumeration used by performance utilities."""

    NONE = "none"
    CUDA = "cuda"
    METAL = "metal"
    OPENCL = "opencl"


def _detect_gpu() -> _GPUBackend:
    """Detect the best available GPU backend without importing heavy libs eagerly."""
    # CUDA via cupy (lightweight check)
    try:
        import cupy as cp  # type: ignore[import-untyped]

        if cp.cuda.runtime.getDeviceCount() > 0:
            return _GPUBackend.CUDA
    except Exception:
        pass

    # CUDA via pycuda
    try:
        import pycuda.driver as cuda  # type: ignore[import-untyped]

        cuda.init()
        if cuda.Device.count() > 0:
            return _GPUBackend.CUDA
    except Exception:
        pass

    # Metal (macOS)
    if sys.platform == "darwin":
        try:
            import metal  # type: ignore[import-untyped]

            return _GPUBackend.METAL
        except Exception:
            # No common Python Metal binding installed; fall through.
            pass

    # OpenCL
    try:
        import pyopencl as cl  # type: ignore[import-untyped]

        platforms = cl.get_platforms()
        if platforms:
            return _GPUBackend.OPENCL
    except Exception:
        pass

    return _GPUBackend.NONE


def _gpu_available() -> bool:
    """Quick check whether any GPU backend is available."""
    return _detect_gpu() != _GPUBackend.NONE


# ---------------------------------------------------------------------------
# PerformanceMonitor
# ---------------------------------------------------------------------------


class PerformanceMonitor:
    """Monitor memory and estimate conversion performance."""

    def __init__(self, max_memory_mb: int = 1024) -> None:
        """Initialize the monitor with a memory ceiling.

        Parameters
        ----------
        max_memory_mb:
            Maximum allowed memory usage in megabytes.
        """
        self.max_memory_mb = max_memory_mb

    def check_memory(self) -> dict[str, float]:
        """Check current memory usage.

        Returns
        -------
        dict
            Keys: ``used_mb``, ``available_mb``, ``limit_mb``, ``percent``.
        """
        try:
            import psutil  # type: ignore[import-untyped]

            mem = psutil.virtual_memory()
            used_mb = mem.used / (1024 * 1024)
            available_mb = mem.available / (1024 * 1024)
            limit_mb = float(self.max_memory_mb)
            percent = (used_mb / limit_mb * 100) if limit_mb > 0 else 0.0
            return {
                "used_mb": round(used_mb, 2),
                "available_mb": round(available_mb, 2),
                "limit_mb": round(limit_mb, 2),
                "percent": round(percent, 2),
            }
        except Exception:
            # Fallback when psutil is unavailable.
            return {
                "used_mb": 0.0,
                "available_mb": float(self.max_memory_mb),
                "limit_mb": float(self.max_memory_mb),
                "percent": 0.0,
            }

    def estimate_conversion_time(
        self, image_size: tuple[int, int], options: TraceOptions
    ) -> float:
        """Estimate tracing time based on image dimensions and options.

        Parameters
        ----------
        image_size:
            ``(width, height)`` in pixels.
        options:
            Tracing options that affect complexity.

        Returns
        -------
        float
            Estimated elapsed time in seconds.
        """
        width, height = image_size
        pixels = width * height
        # Base time + per-pixel factor (empirically tuned heuristic)
        base_time = 0.5
        per_pixel = 0.000_002
        estimated = base_time + pixels * per_pixel

        # Complexity multipliers
        if options.colormode == "color":
            estimated *= 1.5
        if options.mode == "spline":
            estimated *= 1.2
        if options.denoise:
            estimated *= 1.1
        if options.posterize is not None:
            estimated *= 0.9
        estimated *= max(1.0, options.color_precision / 4.0)
        estimated *= max(1.0, options.max_iterations / 10.0)
        return round(estimated, 2)

    def suggest_optimization(self, image_path: Path) -> list[str]:
        """Suggest performance optimizations for a given image.

        Parameters
        ----------
        image_path:
            Path to the source raster image.

        Returns
        -------
        list[str]
            Human-readable recommendations.
        """
        suggestions: list[str] = []
        image_path = Path(image_path)

        if not image_path.exists():
            return suggestions

        try:
            from PIL import Image

            with Image.open(image_path) as img:
                width, height = img.size
                file_size_mb = image_path.stat().st_size / (1024 * 1024)

                if max(width, height) > 5000:
                    suggestions.append(
                        "Image is very large; consider using --max-input-side to downscale before tracing."
                    )
                if file_size_mb > 10:
                    suggestions.append(
                        "File size exceeds 10 MB; streaming/chunked processing is recommended."
                    )
                if img.mode in {"RGBA", "P"}:
                    suggestions.append(
                        "Transparent or paletted image detected; ensure alpha_background is set if needed."
                    )
                if width * height > 10_000_000:
                    suggestions.append(
                        "High-resolution image; reducing color_precision or filter_speckle may speed up conversion."
                    )
        except Exception as exc:
            logger.debug("Could not analyze image for suggestions: %s", exc)

        if not _gpu_available():
            suggestions.append(
                "No GPU detected; install cupy or pyopencl for potential acceleration."
            )
        else:
            suggestions.append(
                f"GPU backend detected ({_detect_gpu().value}); GPU preprocessing is available."
            )

        return suggestions


# ---------------------------------------------------------------------------
# StreamingImageProcessor
# ---------------------------------------------------------------------------


class StreamingImageProcessor:
    """Process oversized images by splitting them into overlapping chunks."""

    # Thresholds that trigger streaming mode
    SIZE_THRESHOLD_MB = 10.0
    DIMENSION_THRESHOLD_PX = 5000
    OVERLAP_PX = 64

    def process_large_image(
        self,
        input_path: Path,
        output_path: Path,
        options: TraceOptions,
        chunk_size: int = 1024,
    ) -> Path:
        """Trace a large image in overlapping chunks and merge the resulting SVGs.

        Parameters
        ----------
        input_path:
            Source raster image.
        output_path:
            Destination SVG path.
        options:
            Tracing options applied to each chunk.
        chunk_size:
            Maximum width/height of each chunk in pixels.

        Returns
        -------
        Path
            The merged output SVG path.
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        from PIL import Image

        with Image.open(input_path) as img:
            width, height = img.size

        # If image is small enough, fall back to regular tracing.
        if not self._should_stream(input_path, (width, height)):
            from .tracer import trace_image

            result = trace_image(input_path, output_path, options)
            return result.svg_path

        import tempfile

        chunk_svgs: list[tuple[Path, int, int]] = []
        with tempfile.TemporaryDirectory(prefix="vector-studio-stream-") as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Generate overlapping chunks
            y = 0
            while y < height:
                x = 0
                chunk_h = min(chunk_size, height - y)
                while x < width:
                    chunk_w = min(chunk_size, width - x)
                    # Expand chunk by overlap on all sides except image borders
                    crop_x = max(0, x - self.OVERLAP_PX)
                    crop_y = max(0, y - self.OVERLAP_PX)
                    crop_x2 = min(width, x + chunk_w + self.OVERLAP_PX)
                    crop_y2 = min(height, y + chunk_h + self.OVERLAP_PX)

                    with Image.open(input_path) as img:
                        chunk = img.crop((crop_x, crop_y, crop_x2, crop_y2))
                        chunk_path = tmpdir_path / f"chunk_{x}_{y}.png"
                        chunk.save(chunk_path, format="PNG", optimize=True)

                    chunk_svg = tmpdir_path / f"chunk_{x}_{y}.svg"
                    from .tracer import trace_image

                    result = trace_image(chunk_path, chunk_svg, options, optimize=False)
                    chunk_svgs.append((result.svg_path, x, y))

                    x += chunk_w
                y += chunk_h

            # Merge chunk SVGs into a single document
            self._merge_chunk_svgs(chunk_svgs, output_path, (width, height))

        return output_path

    @classmethod
    def _should_stream(cls, image_path: Path, image_size: tuple[int, int] | None = None) -> bool:
        """Determine whether an image should be processed in streaming mode."""
        file_size_mb = image_path.stat().st_size / (1024 * 1024)
        if file_size_mb > cls.SIZE_THRESHOLD_MB:
            return True
        if image_size is not None:
            width, height = image_size
            if max(width, height) > cls.DIMENSION_THRESHOLD_PX:
                return True
        return False

    @staticmethod
    def _merge_chunk_svgs(
        chunk_svgs: list[tuple[Path, int, int]],
        output_path: Path,
        original_size: tuple[int, int],
    ) -> Path:
        """Merge multiple chunk SVGs into one document using ``<g transform>`` groups."""
        import xml.etree.ElementTree as ET

        _SVG_NS = "http://www.w3.org/2000/svg"
        ET.register_namespace("", _SVG_NS)

        width, height = original_size
        root = ET.Element(f"{{{_SVG_NS}}}svg")
        root.set("xmlns", _SVG_NS)
        root.set("viewBox", f"0 0 {width} {height}")
        root.set("width", str(width))
        root.set("height", str(height))

        for chunk_svg, offset_x, offset_y in chunk_svgs:
            try:
                tree = ET.parse(chunk_svg)
                chunk_root = tree.getroot()
            except ET.ParseError as exc:
                logger.warning("Skipping unparsable chunk SVG %s: %s", chunk_svg, exc)
                continue

            group = ET.SubElement(root, f"{{{_SVG_NS}}}g")
            group.set("transform", f"translate({offset_x}, {offset_y})")

            for child in list(chunk_root):
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag in {"metadata", "title", "desc", "defs"}:
                    continue
                group.append(child)

        tree = ET.ElementTree(root)
        tree.write(output_path, encoding="utf-8", xml_declaration=True)
        return output_path


# ---------------------------------------------------------------------------
# LazyModuleLoader
# ---------------------------------------------------------------------------


class LazyModuleLoader:
    """Lazy loader that imports modules on first access and can unload them."""

    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}
        self._core_modules: set[str] = set()

    def load(self, module_name: str) -> Any:
        """Return the module, importing it on first use.

        Parameters
        ----------
        module_name:
            Fully-qualified Python module name.

        Returns
        -------
        module
            The imported module object.
        """
        if module_name not in self._cache:
            self._cache[module_name] = importlib.import_module(module_name)
        return self._cache[module_name]

    def unload(self, module_name: str) -> None:
        """Remove a module from the cache and ``sys.modules`` to free memory.

        Parameters
        ----------
        module_name:
            Module to evict.
        """
        self._cache.pop(module_name, None)
        # Only remove from sys.modules if it is not a core module.
        if module_name not in self._core_modules and module_name in sys.modules:
            del sys.modules[module_name]

    def preload_core_modules(self) -> None:
        """Preload modules that are required for every conversion."""
        core = [
            "PIL.Image",
            "PIL.ImageFilter",
            "PIL.ImageOps",
            "vector_studio.models",
            "vector_studio.tracer",
            "vector_studio.preprocess",
        ]
        for name in core:
            try:
                self.load(name)
                self._core_modules.add(name)
            except Exception as exc:
                logger.debug("Failed to preload core module %s: %s", name, exc)

    def is_loaded(self, module_name: str) -> bool:
        """Check whether a module is currently cached."""
        return module_name in self._cache
