from pathlib import Path

import pytest
from PIL import Image

from vector_studio.smart_background import (
    detect_background_color,
    is_likely_logo,
    remove_background,
)


class TestDetectBackgroundColor:
    def test_detects_white_background(self):
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        result = detect_background_color(img)
        assert result == "#ffffff"

    def test_detects_black_background(self):
        img = Image.new("RGB", (100, 100), color=(0, 0, 0))
        result = detect_background_color(img)
        assert result == "#000000"

    def test_returns_none_for_rgba(self):
        img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        result = detect_background_color(img)
        assert result is None

    def test_detects_red_background_with_center_object(self):
        img = Image.new("RGB", (100, 100), color=(255, 0, 0))
        # Draw a blue square in the center
        for x in range(30, 70):
            for y in range(30, 70):
                img.putpixel((x, y), (0, 0, 255))
        result = detect_background_color(img)
        assert result == "#ff0000"

    def test_tiny_image_falls_back_to_corner(self):
        img = Image.new("RGB", (2, 2), color=(128, 128, 128))
        result = detect_background_color(img)
        assert result == "#808080"


class TestRemoveBackground:
    def test_removes_uniform_background(self, tmp_path: Path):
        img_path = tmp_path / "input.png"
        out_path = tmp_path / "output.png"
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        # Red circle in center
        for x in range(100):
            for y in range(100):
                if (x - 50) ** 2 + (y - 50) ** 2 <= 900:
                    img.putpixel((x, y), (255, 0, 0))
        img.save(img_path, format="PNG")

        result = remove_background(img_path, out_path, tolerance=30)
        assert result.exists()

        with Image.open(result) as out:
            assert out.mode == "RGBA"
            # Corner should be transparent
            assert out.getpixel((0, 0))[3] < 50
            # Center should be opaque red
            r, g, b, a = out.getpixel((50, 50))
            assert a > 200
            assert r > 200

    def test_preserves_existing_alpha(self, tmp_path: Path):
        img_path = tmp_path / "input.png"
        out_path = tmp_path / "output.png"
        img = Image.new("RGBA", (50, 50), (0, 0, 0, 0))
        img.save(img_path, format="PNG")

        result = remove_background(img_path, out_path)
        with Image.open(result) as out:
            assert out.mode == "RGBA"

    def test_creates_output_directory(self, tmp_path: Path):
        img_path = tmp_path / "input.png"
        out_path = tmp_path / "subdir" / "output.png"
        Image.new("RGB", (10, 10), color=(255, 255, 255)).save(img_path, format="PNG")

        result = remove_background(img_path, out_path)
        assert result.exists()

    def test_tolerance_controls_strictness(self, tmp_path: Path):
        img_path = tmp_path / "input.png"
        out_path = tmp_path / "output.png"
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        # Slightly off-white edge pixel
        img.putpixel((0, 0), (240, 240, 240))
        img.save(img_path, format="PNG")

        result_loose = remove_background(img_path, out_path, tolerance=50)
        with Image.open(result_loose) as out:
            # With high tolerance, near-white becomes transparent
            assert out.getpixel((0, 0))[3] < 100

        result_strict = remove_background(img_path, out_path, tolerance=5)
        with Image.open(result_strict) as out:
            # With low tolerance, near-white stays opaque
            assert out.getpixel((0, 0))[3] > 100


class TestIsLikelyLogo:
    def test_simple_logo_detected(self):
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        # Black square center
        for x in range(30, 70):
            for y in range(30, 70):
                img.putpixel((x, y), (0, 0, 0))
        is_logo, reason = is_likely_logo(img)
        assert is_logo is True
        assert "logo" in reason.lower() or "few colors" in reason.lower()

    def test_photo_rejected(self):
        # Gradient image with many colors
        img = Image.new("RGB", (200, 150))
        for x in range(200):
            for y in range(150):
                img.putpixel((x, y), (x % 256, y % 256, 128))
        is_logo, reason = is_likely_logo(img)
        assert is_logo is False
        assert "not logo-like" in reason.lower()

    def test_wide_image_less_likely_logo(self):
        img = Image.new("RGB", (300, 50), color=(255, 255, 255))
        for x in range(100, 200):
            for y in range(10, 40):
                img.putpixel((x, y), (0, 0, 0))
        is_logo, reason = is_likely_logo(img)
        # Wide aspect ratio reduces logo score
        assert is_logo is False or "near-square" not in reason.lower()

    def test_nearly_square_icon_likely_logo(self):
        img = Image.new("RGB", (64, 64), color=(0, 0, 255))
        for x in range(20, 44):
            for y in range(20, 44):
                img.putpixel((x, y), (255, 255, 0))
        is_logo, reason = is_likely_logo(img)
        assert is_logo is True

    def test_returns_tuple_with_reason(self):
        img = Image.new("RGB", (10, 10), color=(128, 128, 128))
        result = is_likely_logo(img)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)
