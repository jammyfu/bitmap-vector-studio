from pathlib import Path

import pytest

from vector_studio.svg_3d import ARPreview, SVG3D


class TestSVG3D:
    def test_extrude_returns_svg(self, tmp_path: Path):
        svg = tmp_path / "sample.svg"
        svg.write_text('<svg viewBox="0 0 10 10"><rect width="10" height="10"/></svg>')
        engine = SVG3D()
        result = engine.extrude(svg, depth=5.0)
        assert "<svg" in result
        assert "extrude-shadow" in result

    def test_rotate_returns_svg(self, tmp_path: Path):
        svg = tmp_path / "sample.svg"
        svg.write_text('<svg viewBox="0 0 10 10"><rect width="10" height="10"/></svg>')
        engine = SVG3D()
        result = engine.rotate(svg, axis="z", angle=45.0)
        assert "<svg" in result
        assert "matrix" in result

    def test_rotate_x_axis(self, tmp_path: Path):
        svg = tmp_path / "sample.svg"
        svg.write_text('<svg viewBox="0 0 10 10"><rect width="10" height="10"/></svg>')
        engine = SVG3D()
        result = engine.rotate(svg, axis="x", angle=30.0)
        assert "<svg" in result
        assert "matrix" in result

    def test_add_lighting_returns_svg(self, tmp_path: Path):
        svg = tmp_path / "sample.svg"
        svg.write_text('<svg viewBox="0 0 10 10"><rect width="10" height="10"/></svg>')
        engine = SVG3D()
        result = engine.add_lighting(svg, light_direction=(1.0, 0.5, 0.5))
        assert "<svg" in result
        assert "3d-lighting" in result
        assert "feDiffuseLighting" in result

    def test_perspective_returns_svg(self, tmp_path: Path):
        svg = tmp_path / "sample.svg"
        svg.write_text('<svg viewBox="0 0 10 10"><rect width="10" height="10"/></svg>')
        engine = SVG3D()
        result = engine.perspective(svg, fov=60.0)
        assert "<svg" in result
        assert "matrix" in result

    def test_extrude_preserves_invalid_svg(self, tmp_path: Path):
        svg = tmp_path / "broken.svg"
        svg.write_text("not an svg")
        engine = SVG3D()
        result = engine.extrude(svg, depth=5.0)
        assert result == "not an svg"


class TestARPreview:
    def test_create_ar_overlay(self, tmp_path: Path):
        svg = tmp_path / "sample.svg"
        svg.write_text('<svg viewBox="0 0 100 100" width="100" height="100"><rect width="100" height="100"/></svg>')
        ar = ARPreview()
        overlay = ar.create_ar_overlay(svg, width=50.0)
        assert overlay["type"] == "svg_overlay"
        assert overlay["physical_width_mm"] == 50.0
        assert overlay["physical_height_mm"] == 50.0

    def test_export_usdz(self, tmp_path: Path):
        svg = tmp_path / "sample.svg"
        svg.write_text('<svg viewBox="0 0 10 10"><rect width="10" height="10"/></svg>')
        out = tmp_path / "preview.usdz"
        ar = ARPreview()
        result = ar.export_usdz(svg, out)
        assert result == out
        assert out.exists()

    def test_generate_ar_marker(self, tmp_path: Path):
        svg = tmp_path / "sample.svg"
        svg.write_text('<svg viewBox="0 0 10 10"><rect width="10" height="10"/></svg>')
        ar = ARPreview()
        marker = ar.generate_ar_marker(svg)
        assert isinstance(marker, bytes)
        assert len(marker) > 0
        # PNG magic bytes
        assert marker[:8] == b"\x89PNG\r\n\x1a\n"

    def test_generate_ar_marker_missing_file(self, tmp_path: Path):
        ar = ARPreview()
        with pytest.raises(FileNotFoundError):
            ar.generate_ar_marker(tmp_path / "missing.svg")
