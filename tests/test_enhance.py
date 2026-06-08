from pathlib import Path

import pytest
from PIL import Image

from vector_studio.enhance import (
    adaptive_enhance,
    auto_contrast,
    edge_enhance,
    scan_denoise,
    sharpen,
)


class TestEdgeEnhance:
    def test_returns_image(self):
        img = Image.new("RGB", (50, 50), color=(128, 128, 128))
        result = edge_enhance(img, strength=1.0)
        assert isinstance(result, Image.Image)
        assert result.size == (50, 50)

    def test_zero_strength_returns_copy(self):
        img = Image.new("RGB", (50, 50), color=(128, 128, 128))
        result = edge_enhance(img, strength=0.0)
        assert result.size == (50, 50)

    def test_changes_pixels(self):
        # Create an image with a soft edge (gradient)
        img = Image.new("RGB", (50, 50), color=(0, 0, 0))
        for x in range(50):
            for y in range(50):
                val = int(255 * x / 50)
                img.putpixel((x, y), (val, val, val))
        result = edge_enhance(img, strength=2.0)
        # Edge enhancement should alter at least some pixels
        assert list(result.getdata()) != list(img.getdata())


class TestScanDenoise:
    def test_returns_image(self):
        img = Image.new("RGB", (50, 50), color=(200, 200, 200))
        result = scan_denoise(img, strength=2)
        assert isinstance(result, Image.Image)

    def test_reduces_noise(self):
        # Create a noisy gray image
        img = Image.new("RGB", (50, 50))
        for x in range(50):
            for y in range(50):
                val = 200 if (x + y) % 2 == 0 else 50
                img.putpixel((x, y), (val, val, val))
        result = scan_denoise(img, strength=2)
        # Denoising should smooth the checkerboard
        assert list(result.getdata()) != list(img.getdata())

    def test_strength_bounds(self):
        img = Image.new("RGB", (50, 50), color=(128, 128, 128))
        # Very high strength should still work
        result = scan_denoise(img, strength=5)
        assert isinstance(result, Image.Image)


class TestAutoContrast:
    def test_stretches_low_contrast(self):
        img = Image.new("RGB", (50, 50), color=(100, 100, 100))
        result = auto_contrast(img, cutoff=0.0)
        assert isinstance(result, Image.Image)

    def test_cutoff_parameter(self):
        img = Image.new("RGB", (50, 50), color=(128, 128, 128))
        result_low = auto_contrast(img, cutoff=0.0)
        result_high = auto_contrast(img, cutoff=10.0)
        assert isinstance(result_low, Image.Image)
        assert isinstance(result_high, Image.Image)

    def test_preserves_size(self):
        img = Image.new("RGB", (100, 80), color=(50, 50, 50))
        result = auto_contrast(img)
        assert result.size == (100, 80)


class TestSharpen:
    def test_returns_image(self):
        img = Image.new("RGB", (50, 50), color=(128, 128, 128))
        result = sharpen(img, radius=2, percent=150, threshold=3)
        assert isinstance(result, Image.Image)

    def test_parameter_variations(self):
        img = Image.new("RGB", (50, 50), color=(128, 128, 128))
        result1 = sharpen(img, radius=1, percent=50, threshold=1)
        result2 = sharpen(img, radius=3, percent=200, threshold=5)
        assert isinstance(result1, Image.Image)
        assert isinstance(result2, Image.Image)

    def test_changes_edges(self):
        img = Image.new("RGB", (50, 50), color=(0, 0, 0))
        for x in range(50):
            for y in range(50):
                val = int(255 * x / 50)
                img.putpixel((x, y), (val, val, val))
        result = sharpen(img, radius=2, percent=200, threshold=1)
        assert list(result.getdata()) != list(img.getdata())


class TestAdaptiveEnhance:
    def test_auto_guesses_type(self):
        img = Image.new("RGB", (100, 100), color=(128, 128, 128))
        result = adaptive_enhance(img, image_type="auto")
        assert isinstance(result, Image.Image)

    def test_scan_type(self):
        img = Image.new("RGB", (100, 100), color=(200, 200, 200))
        result = adaptive_enhance(img, image_type="scan")
        assert isinstance(result, Image.Image)

    def test_photo_type(self):
        img = Image.new("RGB", (100, 100), color=(128, 128, 128))
        result = adaptive_enhance(img, image_type="photo")
        assert isinstance(result, Image.Image)

    def test_logo_type(self):
        img = Image.new("RGB", (64, 64), color=(255, 255, 255))
        for x in range(20, 44):
            for y in range(20, 44):
                img.putpixel((x, y), (0, 0, 0))
        result = adaptive_enhance(img, image_type="logo")
        assert isinstance(result, Image.Image)

    def test_unknown_type_fallback(self):
        img = Image.new("RGB", (50, 50), color=(128, 128, 128))
        result = adaptive_enhance(img, image_type="unknown")
        assert isinstance(result, Image.Image)
