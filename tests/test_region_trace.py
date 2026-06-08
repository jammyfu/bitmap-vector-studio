from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from vector_studio.models import TraceOptions, TraceResult
from vector_studio.region_trace import (
    RegionSelector,
    crop_region,
    merge_region_svg,
    region_trace,
    trace_region,
)


class TestRegionSelector:
    def test_valid_rect(self):
        r = RegionSelector(x=10, y=20, width=30, height=40)
        assert r.shape == "rect"

    def test_invalid_shape_raises(self):
        with pytest.raises(ValueError, match="shape must be"):
            RegionSelector(x=0, y=0, width=10, height=10, shape="triangle")

    def test_polygon_without_points_raises(self):
        with pytest.raises(ValueError, match="polygon_points"):
            RegionSelector(x=0, y=0, width=10, height=10, shape="polygon")

    def test_polygon_with_few_points_raises(self):
        with pytest.raises(ValueError, match="polygon_points"):
            RegionSelector(x=0, y=0, width=10, height=10, shape="polygon", polygon_points=[(0, 0)])


class TestCropRegion:
    def test_crop_region_rect(self, tmp_path: Path):
        img = tmp_path / "src.png"
        Image.new("RGB", (100, 100), color=(255, 0, 0)).save(img)
        out = tmp_path / "crop.png"
        region = RegionSelector(x=10, y=20, width=30, height=40)
        result = crop_region(img, region, out)
        assert result == out
        assert out.exists()
        with Image.open(out) as im:
            assert im.size == (30, 40)

    def test_crop_region_circle(self, tmp_path: Path):
        img = tmp_path / "src.png"
        Image.new("RGB", (100, 100), color=(0, 255, 0)).save(img)
        out = tmp_path / "crop.png"
        region = RegionSelector(x=10, y=10, width=50, height=50, shape="circle")
        result = crop_region(img, region, out)
        assert result == out
        with Image.open(out) as im:
            assert im.mode == "RGBA"
            assert im.size == (50, 50)

    def test_crop_region_polygon(self, tmp_path: Path):
        img = tmp_path / "src.png"
        Image.new("RGB", (100, 100), color=(0, 0, 255)).save(img)
        out = tmp_path / "crop.png"
        points = [(10, 10), (60, 10), (35, 60)]
        region = RegionSelector(x=10, y=10, width=50, height=50, shape="polygon", polygon_points=points)
        result = crop_region(img, region, out)
        assert result == out
        with Image.open(out) as im:
            assert im.mode == "RGBA"
            assert im.size == (50, 50)


class TestTraceRegion:
    def test_trace_region_calls_trace_image(self, tmp_path: Path):
        img = tmp_path / "src.png"
        Image.new("RGB", (100, 100), color=(128, 128, 128)).save(img)
        out_svg = tmp_path / "out.svg"
        out_svg.write_text("<svg></svg>")

        mock_result = TraceResult(
            input_path=img,
            svg_path=out_svg,
            engine="python-vtracer",
            elapsed_seconds=0.5,
            stats={"paths": 2},
        )

        region = RegionSelector(x=0, y=0, width=50, height=50)
        with patch("vector_studio.region_trace.trace_image", return_value=mock_result) as mock_trace:
            result = trace_region(img, region, out_svg, TraceOptions())

        assert result.svg_path == out_svg
        mock_trace.assert_called_once()
        passed_input = mock_trace.call_args[0][0]
        # The cropped file is inside a temp directory that is already cleaned up,
        # so we only verify the path object type and name.
        assert passed_input.name == "cropped.png"


class TestMergeRegionSvg:
    def test_merge_region_svg_combines_svgs(self, tmp_path: Path):
        original = tmp_path / "orig.svg"
        original.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            '<path d="M0 0 L100 100" stroke="black"/>'
            "</svg>",
            encoding="utf-8",
        )
        region = tmp_path / "region.svg"
        region.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 50 50">'
            '<path d="M0 0 L50 50" stroke="red"/>'
            "</svg>",
            encoding="utf-8",
        )
        out = tmp_path / "merged.svg"
        selector = RegionSelector(x=10, y=20, width=50, height=50)
        result = merge_region_svg(original, region, selector, out)
        assert result == out
        assert out.exists()
        text = out.read_text(encoding="utf-8")
        assert "region-trace" in text
        assert 'translate(10, 20)' in text

    def test_merge_invalid_original_raises(self, tmp_path: Path):
        bad = tmp_path / "bad.svg"
        bad.write_text("not svg")
        region = tmp_path / "region.svg"
        region.write_text("<svg></svg>")
        out = tmp_path / "merged.svg"
        with pytest.raises(ValueError, match="Cannot parse original SVG"):
            merge_region_svg(bad, region, RegionSelector(0, 0, 10, 10), out)


class TestRegionTrace:
    def test_region_trace_without_original(self, tmp_path: Path):
        img = tmp_path / "src.png"
        Image.new("RGB", (100, 100), color=(64, 64, 64)).save(img)
        out = tmp_path / "out.svg"

        mock_result = TraceResult(
            input_path=img,
            svg_path=out,
            engine="python-vtracer",
            elapsed_seconds=0.3,
            stats={"paths": 1},
        )

        def side_effect(input_path, output_path, options):
            output_path.write_text("<svg></svg>")
            return mock_result

        region = RegionSelector(x=10, y=10, width=30, height=30)
        with patch("vector_studio.region_trace.trace_image", side_effect=side_effect) as mock_trace:
            result = region_trace(img, region, out, TraceOptions())

        assert result.svg_path == out
        mock_trace.assert_called_once()

    def test_region_trace_with_original(self, tmp_path: Path):
        img = tmp_path / "src.png"
        Image.new("RGB", (100, 100), color=(64, 64, 64)).save(img)
        original_svg = tmp_path / "original.svg"
        original_svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            '<path d="M0 0 L100 100"/>'
            "</svg>",
            encoding="utf-8",
        )
        out = tmp_path / "out.svg"

        mock_result = TraceResult(
            input_path=img,
            svg_path=out,
            engine="python-vtracer",
            elapsed_seconds=0.3,
            stats={"paths": 1},
        )

        def side_effect(input_path, output_path, options):
            output_path.write_text("<svg></svg>")
            return mock_result

        region = RegionSelector(x=5, y=5, width=20, height=20)
        with patch("vector_studio.region_trace.trace_image", side_effect=side_effect):
            result = region_trace(img, region, out, TraceOptions(), original_svg=original_svg)

        assert result.svg_path == out
        assert out.exists()
        text = out.read_text(encoding="utf-8")
        assert "region-trace" in text

    def test_region_trace_missing_input_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError, match="Input file not found"):
            region_trace(
                tmp_path / "missing.png",
                RegionSelector(0, 0, 10, 10),
                tmp_path / "out.svg",
                TraceOptions(),
            )

    def test_region_trace_missing_original_raises(self, tmp_path: Path):
        img = tmp_path / "src.png"
        Image.new("RGB", (10, 10), color=(0, 0, 0)).save(img)
        with pytest.raises(FileNotFoundError, match="Original SVG not found"):
            region_trace(
                img,
                RegionSelector(0, 0, 5, 5),
                tmp_path / "out.svg",
                TraceOptions(),
                original_svg=tmp_path / "missing.svg",
            )
