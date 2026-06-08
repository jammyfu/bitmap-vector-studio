from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from PIL import Image

from .models import TraceOptions
from .svg_tools import svg_stats

logger = logging.getLogger(__name__)


class VectorEngine(ABC):
    """Abstract base class for vectorization engines.

    Each engine wraps a specific bitmap-to-SVG conversion backend and exposes
    a uniform ``convert()`` interface plus metadata and benchmarking helpers.
    """

    name: str = ""
    version: str = ""
    supported_formats: list[str] = []
    supported_outputs: list[str] = [".svg"]

    @abstractmethod
    def convert(self, input_path: Path, output_path: Path, options: dict[str, Any]) -> dict[str, Any]:
        """Convert a raster image to SVG.

        Parameters
        ----------
        input_path:
            Path to the source bitmap.
        output_path:
            Destination path (should end with ``.svg``).
        options:
            Engine-specific options dictionary.

        Returns
        -------
        dict
            Result metadata such as ``elapsed_seconds`` and ``engine``.
        """
        ...

    def benchmark(self, input_path: Path, options: dict[str, Any]) -> dict[str, Any]:
        """Run a single timed conversion and return performance metrics.

        Parameters
        ----------
        input_path:
            Path to the source bitmap.
        options:
            Engine-specific options dictionary.

        Returns
        -------
        dict
            Metrics including ``elapsed_seconds``, ``file_bytes``, ``paths``,
            and ``engine``.
        """
        start = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="vector-studio-bench-") as tmp:
            out = Path(tmp) / "output.svg"
            meta = self.convert(input_path, out, options)
            stats = svg_stats(out)
            stats["file_bytes"] = out.stat().st_size
        elapsed = time.perf_counter() - start
        return {
            "engine": self.name,
            "elapsed_seconds": elapsed,
            "file_bytes": stats.get("file_bytes", 0),
            "paths": stats.get("paths", 0),
            **meta,
        }

    def get_info(self) -> dict[str, Any]:
        """Return static engine metadata.

        Returns
        -------
        dict
            Dictionary with ``name``, ``version``, ``supported_formats``,
            ``supported_outputs``, and ``available``.
        """
        return {
            "name": self.name,
            "version": self.version,
            "supported_formats": self.supported_formats,
            "supported_outputs": self.supported_outputs,
            "available": self.is_available(),
        }

    @classmethod
    def is_available(cls) -> bool:
        """Check whether the engine can be used on the current system.

        Returns
        -------
        bool
            ``True`` if the engine backend is installed and reachable.
        """
        return True


class VTracerEngine(VectorEngine):
    """Engine wrapper around VTracer (Python binding or CLI fallback)."""

    name = "vtracer"
    version = "1.0"
    supported_formats = [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"]

    def convert(self, input_path: Path, output_path: Path, options: dict[str, Any]) -> dict[str, Any]:
        """Convert using VTracer Python binding or CLI fallback.

        Parameters
        ----------
        input_path:
            Source bitmap path.
        output_path:
            Destination SVG path.
        options:
            May contain a ``trace_options`` key with a :class:`TraceOptions`
            instance.  Other keys are ignored.

        Returns
        -------
        dict
            Metadata with ``engine`` set to ``"vtracer"``.
        """
        trace_options: TraceOptions = options.get("trace_options", TraceOptions())
        try:
            import vtracer

            vtracer.convert_image_to_svg_py(
                str(input_path), str(output_path), **trace_options.vtracer_kwargs()
            )
        except ImportError:
            executable = shutil.which("vtracer")
            if not executable:
                raise RuntimeError("VTracer is not available (no Python package or CLI on PATH).")
            command = [executable, *trace_options.vtracer_cli_args(input_path, output_path)]
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
            if completed.returncode != 0:
                raise RuntimeError(
                    completed.stderr.strip() or completed.stdout.strip() or "VTracer CLI failed."
                )
        return {"engine": self.name}


class PotraceEngine(VectorEngine):
    """Engine wrapper around the ``potrace`` CLI tool.

    Potrace works best for monochrome / logo-like images.  Colour images are
    converted to greyscale and then to a PBM bitmap before tracing.
    """

    name = "potrace"
    version = "1.0"
    supported_formats = [".png", ".jpg", ".jpeg", ".bmp", ".pbm", ".pgm", ".ppm", ".tif", ".tiff"]

    @classmethod
    def is_available(cls) -> bool:
        return shutil.which("potrace") is not None

    def convert(self, input_path: Path, output_path: Path, options: dict[str, Any]) -> dict[str, Any]:
        """Convert using potrace CLI.

        Steps:
        1. Convert input to PBM (or PGM) via Pillow.
        2. Run ``potrace -s -o output.svg input.pbm``.

        Parameters
        ----------
        input_path:
            Source bitmap path.
        output_path:
            Destination SVG path.
        options:
            Supported keys: ``turdsize`` (int), ``alphamax`` (float),
            ``opticurve`` (bool).

        Returns
        -------
        dict
            Metadata with ``engine`` set to ``"potrace"``.
        """
        if not self.is_available():
            raise RuntimeError("potrace is not installed or not on PATH.")

        with tempfile.TemporaryDirectory(prefix="vector-studio-potrace-") as tmp:
            pbm_path = Path(tmp) / "input.ppm"
            with Image.open(input_path) as img:
                # Potrace expects monochrome; convert to greyscale then 1-bit
                gray = img.convert("L")
                # Use a middle threshold for binarisation
                bw = gray.point(lambda x: 0 if x < 128 else 255, mode="1")
                bw.save(pbm_path, format="PPM")

            cmd = [
                "potrace",
                "-s",
                "-o",
                str(output_path),
                str(pbm_path),
            ]
            if "turdsize" in options:
                cmd.extend(["-t", str(int(options["turdsize"]))])
            if "alphamax" in options:
                cmd.extend(["-a", str(float(options["alphamax"]))])
            if options.get("opticurve", True):
                cmd.append("-O")
            else:
                cmd.append("-O0")

            completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if completed.returncode != 0:
                raise RuntimeError(
                    completed.stderr.strip() or completed.stdout.strip() or "potrace failed."
                )

        return {"engine": self.name}


class AutoTraceEngine(VectorEngine):
    """Engine wrapper around the ``autotrace`` CLI tool.

    AutoTrace tends to produce smooth curves and is a good choice for complex
    illustrations where curve quality matters.
    """

    name = "autotrace"
    version = "1.0"
    supported_formats = [".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".pbm", ".pgm", ".ppm"]

    @classmethod
    def is_available(cls) -> bool:
        return shutil.which("autotrace") is not None

    def convert(self, input_path: Path, output_path: Path, options: dict[str, Any]) -> dict[str, Any]:
        """Convert using autotrace CLI.

        Runs ``autotrace -output-file output.svg input.png`` with optional
        parameter overrides.

        Parameters
        ----------
        input_path:
            Source bitmap path.
        output_path:
            Destination SVG path.
        options:
            Supported keys: ``color_count`` (int), ``despeckle_level`` (int),
            ``corner_threshold`` (int).

        Returns
        -------
        dict
            Metadata with ``engine`` set to ``"autotrace"``.
        """
        if not self.is_available():
            raise RuntimeError("autotrace is not installed or not on PATH.")

        cmd = [
            "autotrace",
            "-output-file",
            str(output_path),
        ]
        if "color_count" in options:
            cmd.extend(["-color-count", str(int(options["color_count"]))])
        if "despeckle_level" in options:
            cmd.extend(["-despeckle-level", str(int(options["despeckle_level"]))])
        if "corner_threshold" in options:
            cmd.extend(["-corner-threshold", str(int(options["corner_threshold"]))])

        cmd.append(str(input_path))

        completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise RuntimeError(
                completed.stderr.strip() or completed.stdout.strip() or "autotrace failed."
            )

        return {"engine": self.name}


class EngineRegistry:
    """Central registry for :class:`VectorEngine` implementations.

    The registry is responsible for discovering, instantiating, and
    recommending engines based on image characteristics.
    """

    def __init__(self) -> None:
        self._engines: dict[str, type[VectorEngine]] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(VTracerEngine)
        self.register(PotraceEngine)
        self.register(AutoTraceEngine)

    def register(self, engine_class: type[VectorEngine]) -> None:
        """Register an engine class by its ``name`` attribute.

        Parameters
        ----------
        engine_class:
            Concrete subclass of :class:`VectorEngine`.
        """
        self._engines[engine_class.name] = engine_class

    def get_engine(self, name: str) -> VectorEngine:
        """Instantiate an engine by name.

        Parameters
        ----------
        name:
            Engine identifier (e.g. ``"vtracer"``, ``"potrace"``).

        Returns
        -------
        VectorEngine
            Fresh instance of the requested engine.

        Raises
        ------
        ValueError
            If the engine name is unknown.
        """
        key = name.strip().lower()
        cls = self._engines.get(key)
        if cls is None:
            valid = ", ".join(sorted(self._engines))
            raise ValueError(f"Unknown engine '{name}'. Available: {valid}.")
        return cls()

    def list_engines(self) -> list[dict[str, Any]]:
        """List metadata for every registered engine.

        Returns
        -------
        list[dict]
            One info dict per engine (see :meth:`VectorEngine.get_info`).
        """
        return [cls().get_info() for cls in self._engines.values()]

    def get_best_engine(self, image_path: Path, image_type: str | None = None) -> VectorEngine:
        """Recommend the most suitable engine for a given image.

        Heuristics:
        * ``logo`` / ``lineart`` / ``sketch`` → :class:`PotraceEngine` (sharp B/W).
        * ``photo`` / ``gradient`` → :class:`VTracerEngine` (colour support).
        * ``complex`` / ``illustration`` → :class:`AutoTraceEngine` (curve quality).
        * Fallback → :class:`VTracerEngine`.

        Parameters
        ----------
        image_path:
            Path to the source image (used when ``image_type`` is ``None``).
        image_type:
            Optional explicit category string.

        Returns
        -------
        VectorEngine
            Instance of the recommended engine.
        """
        if image_type is None:
            image_type = self._detect_image_type(image_path)

        image_type = image_type.lower().strip()

        if image_type in {"logo", "lineart", "line_art", "sketch", "bw", "binary"}:
            if PotraceEngine.is_available():
                return PotraceEngine()
        elif image_type in {"photo", "gradient", "gradient_bands", "color"}:
            if VTracerEngine.is_available():
                return VTracerEngine()
        elif image_type in {"complex", "illustration", "art", "drawing"}:
            if AutoTraceEngine.is_available():
                return AutoTraceEngine()
            if VTracerEngine.is_available():
                return VTracerEngine()

        # Fallback chain
        if VTracerEngine.is_available():
            return VTracerEngine()
        if PotraceEngine.is_available():
            return PotraceEngine()
        if AutoTraceEngine.is_available():
            return AutoTraceEngine()

        raise RuntimeError("No vectorization engine is available.")

    @staticmethod
    def _detect_image_type(image_path: Path) -> str:
        """Simple heuristic to guess image category from file metadata.

        Parameters
        ----------
        image_path:
            Path to the source image.

        Returns
        -------
        str
            Guessed category (``photo``, ``logo``, ``complex``).
        """
        try:
            with Image.open(image_path) as img:
                mode = img.mode
                # Paletted or 1-bit images are often logos / line-art
                if mode in ("1", "P", "L"):
                    return "logo"
                # RGBA with few colours often indicates a logo
                if mode == "RGBA":
                    # Quick sample: convert to palette and count colours
                    sample = img.convert("P", palette=Image.ADAPTIVE, colors=256)
                    # This is a rough proxy; real detection would need more work
                    return "logo"
                # Large images with many colours are usually photos
                if img.width * img.height > 1_000_000:
                    return "photo"
                return "complex"
        except Exception:
            return "photo"


class EngineBenchmark:
    """Benchmark harness that compares multiple engines on the same input."""

    def __init__(self, registry: EngineRegistry | None = None) -> None:
        self.registry = registry or EngineRegistry()

    def compare_engines(
        self,
        input_path: Path,
        engines: list[str] | None = None,
        options: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Run the same image through several engines and collect metrics.

        Parameters
        ----------
        input_path:
            Source bitmap.
        engines:
            List of engine names to compare.  ``None`` means all available
            engines.
        options:
            Base options dictionary passed to each engine's ``convert()``.

        Returns
        -------
        list[dict]
            One result dict per engine, sorted by elapsed time (fastest first).
        """
        options = options or {}
        if engines is None:
            engines = [
                info["name"]
                for info in self.registry.list_engines()
                if info["available"]
            ]

        results: list[dict[str, Any]] = []
        for name in engines:
            engine = self.registry.get_engine(name)
            if not engine.is_available():
                results.append({
                    "engine": name,
                    "available": False,
                    "error": "Engine not available",
                })
                continue
            try:
                bench = engine.benchmark(input_path, options)
                # Approximate visual quality score (higher = better)
                # Heuristic: moderate file size, moderate path count
                file_bytes = bench.get("file_bytes", 1)
                paths = bench.get("paths", 1)
                # Simple composite: penalise tiny or huge outputs
                size_score = max(0, 100 - abs(file_bytes - 5000) / 500)
                path_score = max(0, 100 - abs(paths - 50) * 2)
                bench["quality_score"] = round((size_score + path_score) / 2, 1)
                results.append(bench)
            except Exception as exc:
                results.append({
                    "engine": name,
                    "available": True,
                    "error": str(exc),
                })

        # Sort by elapsed time, keeping errors at the end
        def sort_key(r: dict[str, Any]) -> tuple[bool, float]:
            has_error = "error" in r
            elapsed = r.get("elapsed_seconds", float("inf"))
            return (has_error, elapsed)

        results.sort(key=sort_key)
        return results

    def run_full_benchmark(
        self,
        input_dir: Path,
        output_dir: Path,
        engines: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run a full benchmark suite over every image in *input_dir*.

        Parameters
        ----------
        input_dir:
            Directory containing test bitmaps.
        output_dir:
            Directory where per-engine SVG outputs are saved.
        engines:
            Engine names to include.  ``None`` means all available engines.

        Returns
        -------
        dict
            Summary with per-image and per-engine aggregates.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        images = [
            p for p in input_dir.iterdir()
            if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
        ]

        per_image: dict[str, list[dict[str, Any]]] = {}
        per_engine: dict[str, list[dict[str, Any]]] = {}

        for img in images:
            results = self.compare_engines(img, engines=engines)
            per_image[img.name] = results
            for r in results:
                en = r["engine"]
                per_engine.setdefault(en, []).append(r)

        # Aggregates
        summary: dict[str, Any] = {
            "images_tested": len(images),
            "engines": list(per_engine.keys()),
            "per_image": per_image,
        }

        for en, runs in per_engine.items():
            valid = [r for r in runs if "error" not in r]
            if valid:
                summary[en] = {
                    "mean_time": sum(r["elapsed_seconds"] for r in valid) / len(valid),
                    "mean_paths": sum(r.get("paths", 0) for r in valid) / len(valid),
                    "mean_size": sum(r.get("file_bytes", 0) for r in valid) / len(valid),
                    "success_rate": len(valid) / len(runs),
                }
            else:
                summary[en] = {"success_rate": 0.0}

        return summary


# Global singleton for convenient import
default_registry = EngineRegistry()
