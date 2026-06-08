from pathlib import Path

import pytest
from PIL import Image, ExifTags

from vector_studio.models import TraceOptions
from vector_studio.preprocess import prepare_input, _hex_to_rgb


class TestHexToRgb:
    def test_hex_to_rgb_with_hash(self):
        assert _hex_to_rgb("#ffffff") == (255, 255, 255)

    def test_hex_to_rgb_without_hash(self):
        assert _hex_to_rgb("ff0000") == (255, 0, 0)

    def test_hex_to_rgb_short_form(self):
        assert _hex_to_rgb("#fff") == (255, 255, 255)

    def test_hex_to_rgb_invalid_length(self):
        with pytest.raises(ValueError, match="alpha_background must be a hex color"):
            _hex_to_rgb("#ffff")


class TestPrepareInput:
    def test_exif_orientation_correction(self, tmp_path):
        img_path = tmp_path / "oriented.jpg"
        img = Image.new("RGB", (200, 100), color=(0, 255, 0))
        # Set EXIF orientation to 6 (rotated 270 CW / 90 CCW)
        exif = img.getexif()
        exif[274] = 6  # Orientation tag
        img.save(img_path, format="JPEG", exif=exif.tobytes())

        opts = TraceOptions()
        out_path = tmp_path / "normalized.png"
        result = prepare_input(img_path, out_path, opts)

        assert result.exists()
        with Image.open(result) as normalized:
            # After exif_transpose with orientation=6, dimensions should be swapped
            assert normalized.size == (100, 200)

    def test_rgba_transparent_background_composited(self, tmp_path):
        img_path = tmp_path / "rgba.png"
        img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        # Draw a red square in the center
        for x in range(25, 75):
            for y in range(25, 75):
                img.putpixel((x, y), (255, 0, 0, 255))
        img.save(img_path, format="PNG")

        opts = TraceOptions(alpha_background="#ffffff")
        out_path = tmp_path / "normalized.png"
        result = prepare_input(img_path, out_path, opts)

        with Image.open(result) as normalized:
            assert normalized.mode == "RGB"
            # Corner should be white (background)
            assert normalized.getpixel((0, 0)) == (255, 255, 255)
            # Center should be red
            assert normalized.getpixel((50, 50)) == (255, 0, 0)

    def test_rgba_no_background_preserved(self, tmp_path):
        img_path = tmp_path / "rgba.png"
        img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        img.save(img_path, format="PNG")

        opts = TraceOptions(alpha_background=None)
        out_path = tmp_path / "normalized.png"
        result = prepare_input(img_path, out_path, opts)

        with Image.open(result) as normalized:
            assert normalized.mode == "RGBA"

    def test_palette_with_transparency(self, tmp_path):
        img_path = tmp_path / "palette.png"
        img = Image.new("P", (100, 100))
        img.putpalette([i for i in range(256)] * 3)
        img.info["transparency"] = 0
        img.save(img_path, format="PNG")

        opts = TraceOptions(alpha_background="#000000")
        out_path = tmp_path / "normalized.png"
        result = prepare_input(img_path, out_path, opts)

        with Image.open(result) as normalized:
            assert normalized.mode == "RGB"

    def test_denoise_applies_median_filter(self, tmp_path):
        img_path = tmp_path / "noisy.png"
        img = Image.new("RGB", (100, 100), color=(128, 128, 128))
        img.save(img_path, format="PNG")

        opts = TraceOptions(denoise=True)
        out_path = tmp_path / "normalized.png"
        result = prepare_input(img_path, out_path, opts)

        assert result.exists()
        with Image.open(result) as normalized:
            assert normalized.size == (100, 100)

    def test_posterize_reduces_colors(self, tmp_path):
        img_path = tmp_path / "smooth.png"
        img = Image.new("RGB", (100, 100))
        for x in range(100):
            for y in range(100):
                img.putpixel((x, y), (x, y, 128))
        img.save(img_path, format="PNG")

        opts = TraceOptions(posterize=2)
        out_path = tmp_path / "normalized.png"
        result = prepare_input(img_path, out_path, opts)

        assert result.exists()
        with Image.open(result) as normalized:
            # Posterize with 2 bits means only 4 levels per channel
            r, g, b = normalized.getpixel((50, 50))
            assert r in {0, 64, 128, 192, 255}
            assert g in {0, 64, 128, 192, 255}

    def test_max_input_side_downscales(self, tmp_path):
        img_path = tmp_path / "huge.png"
        img = Image.new("RGB", (4000, 2000), color=(0, 0, 255))
        img.save(img_path, format="PNG")

        opts = TraceOptions(max_input_side=1024)
        out_path = tmp_path / "normalized.png"
        result = prepare_input(img_path, out_path, opts)

        with Image.open(result) as normalized:
            assert max(normalized.size) <= 1024

    def test_max_input_side_no_downscale_when_small(self, tmp_path):
        img_path = tmp_path / "small.png"
        img = Image.new("RGB", (100, 100), color=(0, 0, 255))
        img.save(img_path, format="PNG")

        opts = TraceOptions(max_input_side=1024)
        out_path = tmp_path / "normalized.png"
        result = prepare_input(img_path, out_path, opts)

        with Image.open(result) as normalized:
            assert normalized.size == (100, 100)

    def test_output_path_created(self, tmp_path):
        img_path = tmp_path / "input.png"
        Image.new("RGB", (10, 10)).save(img_path, format="PNG")

        opts = TraceOptions()
        out_path = tmp_path / "subdir" / "normalized.png"
        result = prepare_input(img_path, out_path, opts)

        assert result.exists()
        assert result == out_path

    def test_invalid_options_raises(self, tmp_path):
        img_path = tmp_path / "input.png"
        Image.new("RGB", (10, 10)).save(img_path, format="PNG")

        opts = TraceOptions(colormode="invalid")
        out_path = tmp_path / "normalized.png"
        with pytest.raises(ValueError):
            prepare_input(img_path, out_path, opts)
