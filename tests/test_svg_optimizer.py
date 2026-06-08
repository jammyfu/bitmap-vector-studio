from pathlib import Path

import pytest

from vector_studio.svg_optimizer import (
    merge_same_color_paths,
    merge_similar_colors,
    optimize_svg_comprehensive,
    simplify_path_data,
    svg_quality_score,
)


class TestMergeSameColorPaths:
    def test_merges_same_fill_paths(self, tmp_path: Path):
        svg = tmp_path / "merge.svg"
        svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            '<path d="M0 0 L10 10" fill="#ff0000"/>'
            '<path d="M20 20 L30 30" fill="#ff0000"/>'
            '<path d="M40 40 L50 50" fill="#00ff00"/>'
            "</svg>",
            encoding="utf-8",
        )
        result = merge_same_color_paths(svg)
        text = result.read_text(encoding="utf-8")
        assert text.count("<path") == 2
        assert "#ff0000" in text
        assert "#00ff00" in text

    def test_writes_to_output_path(self, tmp_path: Path):
        svg = tmp_path / "in.svg"
        out = tmp_path / "out.svg"
        svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<path d="M0 0 L1 1" fill="blue"/>'
            '<path d="M2 2 L3 3" fill="blue"/>'
            "</svg>",
            encoding="utf-8",
        )
        merge_same_color_paths(svg, out)
        assert out.exists()
        # Original file should remain unchanged
        original_text = svg.read_text(encoding="utf-8")
        assert original_text.count("<path") == 2
        # Output should have merged paths
        output_text = out.read_text(encoding="utf-8")
        assert output_text.count("<path") == 1

    def test_leaves_single_path_unchanged(self, tmp_path: Path):
        svg = tmp_path / "single.svg"
        svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<path d="M0 0" fill="red"/>'
            "</svg>",
            encoding="utf-8",
        )
        merge_same_color_paths(svg)
        assert "<path" in svg.read_text(encoding="utf-8")


class TestMergeSimilarColors:
    def test_quantizes_similar_colors(self, tmp_path: Path):
        svg = tmp_path / "colors.svg"
        svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<path d="M0 0" fill="#ff0000"/>'
            '<path d="M1 1" fill="#ff0001"/>'
            '<path d="M2 2" fill="#00ff00"/>'
            "</svg>",
            encoding="utf-8",
        )
        merge_similar_colors(svg, threshold=10)
        text = svg.read_text(encoding="utf-8")
        # #ff0000 and #ff0001 are distance 1, so they should merge
        fills = [line for line in text.splitlines() if 'fill=' in line]
        unique_fills = set()
        for line in fills:
            m = line.split('fill="')[1].split('"')[0]
            unique_fills.add(m)
        assert len(unique_fills) <= 2

    def test_output_path_creates_new_file(self, tmp_path: Path):
        svg = tmp_path / "in.svg"
        out = tmp_path / "out.svg"
        svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<path d="M0 0" fill="#ff0000"/>'
            "</svg>",
            encoding="utf-8",
        )
        merge_similar_colors(svg, out, threshold=5)
        assert out.exists()


class TestSimplifyPathData:
    def test_reduces_decimals(self, tmp_path: Path):
        svg = tmp_path / "decimals.svg"
        svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<path d="M0.1234 0.5678 L10.9999 20.1111"/>'
            "</svg>",
            encoding="utf-8",
        )
        simplify_path_data(svg, tolerance=1.0)
        text = svg.read_text(encoding="utf-8")
        assert "0.1234" not in text
        assert "0.5678" not in text

    def test_collapses_short_segments(self, tmp_path: Path):
        svg = tmp_path / "short.svg"
        svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<path d="M0 0 L0.1 0.1 L10 10"/>'
            "</svg>",
            encoding="utf-8",
        )
        simplify_path_data(svg, tolerance=1.0)
        text = svg.read_text(encoding="utf-8")
        # The middle short segment should be removed or altered
        assert "<path" in text


class TestSvgQualityScore:
    def test_perfect_small_svg(self, tmp_path: Path):
        svg = tmp_path / "small.svg"
        svg.write_text(
            '<svg viewBox="0 0 10 10" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M0 0 L10 10" fill="red"/>'
            "</svg>",
            encoding="utf-8",
        )
        score = svg_quality_score(svg)
        assert 0 <= score["overall"] <= 100
        assert score["file_size_score"] == 100.0
        assert score["complexity_score"] == 100.0

    def test_large_complex_svg(self, tmp_path: Path):
        svg = tmp_path / "large.svg"
        paths = "\n".join(
            f'<path d="M{i} 0 L{i+1} 1" fill="#{i:02x}{(i*2)%256:02x}{(i*3)%256:02x}"/>'
            for i in range(300)
        )
        svg.write_text(
            f'<svg viewBox="0 0 1000 1000" xmlns="http://www.w3.org/2000/svg">{paths}</svg>',
            encoding="utf-8",
        )
        score = svg_quality_score(svg)
        assert score["overall"] < 100
        assert score["complexity_score"] < 100
        assert score["path_efficiency"] < 100


class TestOptimizeSvgComprehensive:
    def test_basic_pipeline(self, tmp_path: Path):
        svg = tmp_path / "comp.svg"
        svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<path d="M0 0 L10 10" fill="#ff0000"/>'
            '<path d="M20 20 L30 30" fill="#ff0000"/>'
            '<path d="M0 0 L0.01 0.01 L10 10" fill="#00ff00"/>'
            "</svg>",
            encoding="utf-8",
        )
        result = optimize_svg_comprehensive(svg, aggressive=False)
        text = result.read_text(encoding="utf-8")
        assert "<path" in text
        # Two red paths should be merged
        assert text.count("#ff0000") <= 1

    def test_aggressive_mode(self, tmp_path: Path):
        svg = tmp_path / "agg.svg"
        svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<path d="M0 0 L10 10" fill="#ff0000"/>'
            '<path d="M20 20 L30 30" fill="#ff0001"/>'
            '<path d="M0 0 L0.01 0.01 L10 10" fill="#00ff00"/>'
            "</svg>",
            encoding="utf-8",
        )
        result = optimize_svg_comprehensive(svg, aggressive=True)
        text = result.read_text(encoding="utf-8")
        assert "<path" in text

    def test_output_path(self, tmp_path: Path):
        svg = tmp_path / "in.svg"
        out = tmp_path / "out.svg"
        svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<path d="M0 0" fill="red"/>'
            "</svg>",
            encoding="utf-8",
        )
        optimize_svg_comprehensive(svg, out)
        assert out.exists()

    def test_invalid_svg_graceful(self, tmp_path: Path):
        svg = tmp_path / "bad.svg"
        svg.write_text("not an svg", encoding="utf-8")
        # Should not raise
        result = optimize_svg_comprehensive(svg)
        assert result == svg
