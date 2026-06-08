from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from vector_studio.live_preview import LivePreviewEngine, PreviewCache
from vector_studio.models import TraceOptions


class TestPreviewCache:
    def test_cache_hit_rate(self):
        cache = PreviewCache(cache_size=2)
        opts = TraceOptions()
        path = Path("/fake/input.png")
        cache.set(path, opts, b"<svg></svg>")
        assert cache.get(path, opts) == b"<svg></svg>"
        assert cache.stats()["hits"] == 1
        assert cache.stats()["misses"] == 0

    def test_cache_miss(self):
        cache = PreviewCache(cache_size=2)
        opts = TraceOptions()
        path = Path("/fake/input.png")
        assert cache.get(path, opts) is None
        assert cache.stats()["misses"] == 1

    def test_cache_invalidate(self):
        cache = PreviewCache(cache_size=2)
        opts = TraceOptions()
        path = Path("/fake/input.png")
        cache.set(path, opts, b"<svg></svg>")
        cache.invalidate()
        assert cache.get(path, opts) is None
        assert cache.stats()["size"] == 0

    def test_cache_lru_eviction(self):
        cache = PreviewCache(cache_size=2)
        opts1 = TraceOptions(colormode="color")
        opts2 = TraceOptions(colormode="binary")
        opts3 = TraceOptions(mode="polygon")
        p = Path("/fake/input.png")
        cache.set(p, opts1, b"a")
        cache.set(p, opts2, b"b")
        cache.set(p, opts3, b"c")
        assert cache.get(p, opts1) is None
        assert cache.get(p, opts2) == b"b"
        assert cache.get(p, opts3) == b"c"

    def test_cache_ttl_expiration(self):
        cache = PreviewCache(cache_size=2, ttl=-1)
        opts = TraceOptions()
        p = Path("/fake/input.png")
        cache.set(p, opts, b"<svg></svg>")
        assert cache.get(p, opts) is None


class TestLivePreviewEngine:
    def test_missing_input_raises_file_not_found(self):
        engine = LivePreviewEngine()
        with pytest.raises(FileNotFoundError, match="Input file not found"):
            engine.generate_preview(Path("/nonexistent/image.png"), TraceOptions())

    def test_generate_preview_creates_svg(self, tmp_path: Path):
        img = tmp_path / "image.png"
        Image.new("RGB", (800, 600), color=(0, 255, 0)).save(img)
        out_svg = tmp_path / "preview.svg"
        out_svg.write_text("<svg></svg>")

        mock_result = MagicMock()
        mock_result.svg_path = out_svg

        engine = LivePreviewEngine(max_size=200)
        with patch("vector_studio.live_preview.trace_image", return_value=mock_result) as mock_trace:
            preview_path, elapsed = engine.generate_preview(img, TraceOptions())

        assert preview_path.exists()
        assert preview_path.read_bytes() == b"<svg></svg>"
        assert elapsed >= 0.0
        mock_trace.assert_called_once()
        passed_opts = mock_trace.call_args[0][2]
        assert passed_opts.max_input_side == 200

    def test_generate_preview_uses_cache(self, tmp_path: Path):
        img = tmp_path / "image.png"
        Image.new("RGB", (100, 100), color=(255, 0, 0)).save(img)
        out_svg = tmp_path / "preview.svg"
        out_svg.write_text("<svg></svg>")

        mock_result = MagicMock()
        mock_result.svg_path = out_svg

        engine = LivePreviewEngine(max_size=100)
        with patch("vector_studio.live_preview.trace_image", return_value=mock_result) as mock_trace:
            path1, elapsed1 = engine.generate_preview(img, TraceOptions())
            path2, elapsed2 = engine.generate_preview(img, TraceOptions())

        assert mock_trace.call_count == 1
        assert elapsed2 == 0.0
        assert path1.read_bytes() == path2.read_bytes()

    def test_generate_preview_bytes_returns_bytes(self, tmp_path: Path):
        img = tmp_path / "image.png"
        Image.new("RGB", (100, 100), color=(0, 0, 255)).save(img)
        out_svg = tmp_path / "preview.svg"
        out_svg.write_text("<svg></svg>")

        mock_result = MagicMock()
        mock_result.svg_path = out_svg

        engine = LivePreviewEngine(max_size=100)
        with patch("vector_studio.live_preview.trace_image", return_value=mock_result):
            data = engine.generate_preview_bytes(img, TraceOptions())

        assert isinstance(data, bytes)
        assert data == b"<svg></svg>"

    def test_invalidate_cache_clears_entries(self, tmp_path: Path):
        img = tmp_path / "image.png"
        Image.new("RGB", (100, 100), color=(255, 255, 0)).save(img)
        out_svg = tmp_path / "preview.svg"
        out_svg.write_text("<svg></svg>")

        mock_result = MagicMock()
        mock_result.svg_path = out_svg

        engine = LivePreviewEngine(max_size=100)
        with patch("vector_studio.live_preview.trace_image", return_value=mock_result):
            engine.generate_preview(img, TraceOptions())
            engine.invalidate_cache()
            stats = engine.get_cache_stats()

        assert stats["size"] == 0

    def test_get_cache_stats_returns_dict(self, tmp_path: Path):
        img = tmp_path / "image.png"
        Image.new("RGB", (100, 100), color=(255, 0, 255)).save(img)
        out_svg = tmp_path / "preview.svg"
        out_svg.write_text("<svg></svg>")

        mock_result = MagicMock()
        mock_result.svg_path = out_svg

        engine = LivePreviewEngine(max_size=100)
        with patch("vector_studio.live_preview.trace_image", return_value=mock_result):
            engine.generate_preview(img, TraceOptions())
            stats = engine.get_cache_stats()

        assert isinstance(stats, dict)
        assert stats["size"] == 1
        assert stats["max_size"] == 10
        assert "hit_rate" in stats

    def test_preview_respects_max_size(self, tmp_path: Path):
        img = tmp_path / "image.png"
        Image.new("RGB", (1000, 800), color=(128, 128, 128)).save(img)
        out_svg = tmp_path / "preview.svg"
        out_svg.write_text("<svg></svg>")

        mock_result = MagicMock()
        mock_result.svg_path = out_svg

        recorded_size = []

        def side_effect(input_path, *args, **kwargs):
            with Image.open(input_path) as resized:
                recorded_size.append(resized.size)
            return mock_result

        engine = LivePreviewEngine(max_size=150)
        with patch("vector_studio.live_preview.trace_image", side_effect=side_effect) as mock_trace:
            engine.generate_preview(img, TraceOptions())

        assert mock_trace.call_count == 1
        assert max(recorded_size[0]) <= 150
