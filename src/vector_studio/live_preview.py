from __future__ import annotations

import hashlib
import tempfile
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any

from PIL import Image

from .models import TraceOptions, TraceResult
from .tracer import trace_image


class PreviewCache:
    """LRU cache for preview SVG results keyed by a stable parameter hash.

    Entries are automatically evicted when they exceed the TTL (time-to-live).
    """

    def __init__(self, cache_size: int = 10, ttl: int = 300) -> None:
        self.cache_size = cache_size
        self.ttl = ttl
        self._cache: OrderedDict[str, tuple[bytes, float]] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def _make_key(self, input_path: Path, options: TraceOptions) -> str:
        """Create a stable hash key from input path and options."""
        data = f"{input_path.resolve()}:{options.vtracer_kwargs()}:{options.max_input_side}:{options.denoise}:{options.posterize}:{options.alpha_background}"
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def get(self, input_path: Path, options: TraceOptions) -> bytes | None:
        """Retrieve cached SVG bytes if present and not expired."""
        key = self._make_key(input_path, options)
        if key not in self._cache:
            self._misses += 1
            return None
        svg_bytes, timestamp = self._cache[key]
        if time.time() - timestamp > self.ttl:
            del self._cache[key]
            self._misses += 1
            return None
        self._cache.move_to_end(key)
        self._hits += 1
        return svg_bytes

    def set(self, input_path: Path, options: TraceOptions, svg_bytes: bytes) -> None:
        """Store SVG bytes in cache."""
        key = self._make_key(input_path, options)
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = (svg_bytes, time.time())
        while len(self._cache) > self.cache_size:
            self._cache.popitem(last=False)

    def invalidate(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    def stats(self) -> dict[str, Any]:
        """Return cache statistics including hit rate."""
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0.0,
            "size": len(self._cache),
            "max_size": self.cache_size,
        }


class LivePreviewEngine:
    """Fast, low-resolution preview generation with LRU caching.

    Parameters
    ----------
    max_size:
        Maximum edge length for the resized preview image.
    cache_size:
        Number of recent parameter combinations to keep in the LRU cache.
    """

    def __init__(self, max_size: int = 400, cache_size: int = 10) -> None:
        self.max_size = max_size
        self._cache = PreviewCache(cache_size=cache_size, ttl=300)

    def _generate(self, input_path: Path, options: TraceOptions) -> tuple[bytes, float]:
        """Core generation logic. Returns ``(svg_bytes, elapsed_seconds)``."""
        cached = self._cache.get(input_path, options)
        if cached is not None:
            return cached, 0.0

        start = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="vector-studio-preview-") as tmpdir:
            tmpdir_path = Path(tmpdir)
            resized_path = tmpdir_path / "resized.png"

            with Image.open(input_path) as img:
                img.thumbnail((self.max_size, self.max_size), Image.Resampling.LANCZOS)
                img.save(resized_path, format="PNG", optimize=True)

            from dataclasses import asdict

            preview_dict = asdict(options.validate())
            preview_dict["max_input_side"] = self.max_size
            preview_opts = TraceOptions(**preview_dict)

            output_path = tmpdir_path / "preview.svg"
            result = trace_image(
                resized_path,
                output_path,
                preview_opts,
                preview_mode=True,
                optimize=False,
                name_layers=False,
            )
            svg_bytes = result.svg_path.read_bytes()
            self._cache.set(input_path, options, svg_bytes)

        elapsed = time.perf_counter() - start
        return svg_bytes, elapsed

    def generate_preview(self, input_path: Path, options: TraceOptions) -> tuple[Path, float]:
        """Generate a preview SVG and return its path plus elapsed time.

        The result is cached in an LRU cache so repeated calls with the same
        *input_path* and *options* are nearly instant.
        """
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        svg_bytes, elapsed = self._generate(input_path, options)
        key = self._cache._make_key(input_path, options)
        persistent = Path(tempfile.gettempdir()) / f"vs_preview_{key[:16]}.svg"
        persistent.write_bytes(svg_bytes)
        return persistent, elapsed

    def generate_preview_bytes(self, input_path: Path, options: TraceOptions) -> bytes:
        """Return preview SVG as raw bytes for inline GUI display."""
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        svg_bytes, _ = self._generate(input_path, options)
        return svg_bytes

    def invalidate_cache(self) -> None:
        """Clear the preview cache."""
        self._cache.invalidate()

    def get_cache_stats(self) -> dict[str, Any]:
        """Return cache hit/miss statistics."""
        return self._cache.stats()
