from pathlib import Path

import pytest
from PIL import Image

from vector_studio.smart_recommend import (
    analyze_image_features,
    recommend_for_image,
    recommend_preset,
)


class TestAnalyzeImageFeatures:
    def test_basic_dimensions(self, tmp_path: Path):
        img_path = tmp_path / "test.png"
        Image.new("RGB", (200, 100), color=(128, 128, 128)).save(img_path, format="PNG")
        features = analyze_image_features(img_path)
        assert features["width"] == 200
        assert features["height"] == 100
        assert features["aspect_ratio"] == 2.0

    def test_few_colors_detected(self, tmp_path: Path):
        img_path = tmp_path / "test.png"
        img = Image.new("RGB", (100, 100), color=(255, 0, 0))
        img.save(img_path, format="PNG")
        features = analyze_image_features(img_path)
        assert features["color_count"] < 10

    def test_alpha_detection(self, tmp_path: Path):
        img_path = tmp_path / "test.png"
        Image.new("RGBA", (50, 50), (0, 0, 0, 0)).save(img_path, format="PNG")
        features = analyze_image_features(img_path)
        assert features["has_alpha"] is True

    def test_no_alpha_for_rgb(self, tmp_path: Path):
        img_path = tmp_path / "test.png"
        Image.new("RGB", (50, 50), color=(255, 255, 255)).save(img_path, format="PNG")
        features = analyze_image_features(img_path)
        assert features["has_alpha"] is False

    def test_graceful_on_bad_file(self, tmp_path: Path):
        bad_path = tmp_path / "not_an_image.txt"
        bad_path.write_text("hello")
        features = analyze_image_features(bad_path)
        # Should return defaults without crashing
        assert "color_count" in features
        assert features["width"] == 0


class TestRecommendPreset:
    def test_recommends_bw_for_monochrome(self):
        features = {
            "color_count": 2,
            "edge_density": 0.3,
            "aspect_ratio": 1.0,
            "width": 100,
            "height": 100,
            "mean_brightness": 128.0,
            "brightness_std": 50.0,
            "text_like_density": 0.0,
            "is_likely_logo": False,
        }
        preset, confidence, reason = recommend_preset(features)
        assert preset == "bw"
        assert confidence > 0.5

    def test_recommends_logo_for_icon(self):
        features = {
            "color_count": 4,
            "edge_density": 0.25,
            "aspect_ratio": 1.1,
            "width": 128,
            "height": 128,
            "mean_brightness": 128.0,
            "brightness_std": 30.0,
            "text_like_density": 0.0,
            "is_likely_logo": True,
        }
        preset, confidence, reason = recommend_preset(features)
        assert preset == "logo"
        assert confidence > 0.5

    def test_recommends_pixel_art_for_small(self):
        features = {
            "color_count": 8,
            "edge_density": 0.05,
            "aspect_ratio": 1.0,
            "width": 64,
            "height": 64,
            "mean_brightness": 128.0,
            "brightness_std": 20.0,
            "text_like_density": 0.0,
            "is_likely_logo": False,
        }
        preset, confidence, reason = recommend_preset(features)
        assert preset == "pixel_art"
        assert confidence > 0.5

    def test_recommends_photo_for_rich_colors(self):
        features = {
            "color_count": 20,
            "edge_density": 0.1,
            "aspect_ratio": 1.5,
            "width": 800,
            "height": 600,
            "mean_brightness": 128.0,
            "brightness_std": 30.0,
            "text_like_density": 0.0,
            "is_likely_logo": False,
        }
        preset, confidence, reason = recommend_preset(features)
        assert preset == "photo"
        assert confidence > 0.5

    def test_returns_tuple(self):
        features = {
            "color_count": 5,
            "edge_density": 0.1,
            "aspect_ratio": 1.0,
            "width": 100,
            "height": 100,
            "mean_brightness": 128.0,
            "brightness_std": 30.0,
            "text_like_density": 0.0,
            "is_likely_logo": False,
        }
        result = recommend_preset(features)
        assert isinstance(result, tuple)
        assert len(result) == 3
        assert isinstance(result[0], str)
        assert isinstance(result[1], float)
        assert isinstance(result[2], str)


class TestRecommendForImage:
    def test_end_to_end(self, tmp_path: Path):
        img_path = tmp_path / "test.png"
        img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        for x in range(30, 70):
            for y in range(30, 70):
                img.putpixel((x, y), (0, 0, 0))
        img.save(img_path, format="PNG")

        preset, confidence, reason, features = recommend_for_image(img_path)
        assert isinstance(preset, str)
        assert 0.0 <= confidence <= 1.0
        assert isinstance(reason, str)
        assert isinstance(features, dict)
        assert "color_count" in features

    def test_photo_image(self, tmp_path: Path):
        img_path = tmp_path / "test.png"
        # Create a gradient image (photo-like)
        img = Image.new("RGB", (400, 300))
        for x in range(400):
            for y in range(300):
                img.putpixel((x, y), (x % 256, y % 256, 128))
        img.save(img_path, format="PNG")

        preset, confidence, reason, features = recommend_for_image(img_path)
        assert preset in {"photo", "poster"}
        assert confidence > 0.0

    def test_scan_image(self, tmp_path: Path):
        img_path = tmp_path / "test.png"
        # Large low-contrast image with text-like patterns
        img = Image.new("RGB", (1000, 1400), color=(240, 240, 240))
        for x in range(100, 900, 20):
            for y in range(100, 1300, 40):
                for dx in range(15):
                    for dy in range(2):
                        img.putpixel((x + dx, y + dy), (20, 20, 20))
        img.save(img_path, format="PNG")

        preset, confidence, reason, features = recommend_for_image(img_path)
        assert isinstance(preset, str)
        assert confidence >= 0.0

    def test_small_pixel_art(self, tmp_path: Path):
        img_path = tmp_path / "test.png"
        img = Image.new("RGB", (32, 32), color=(0, 0, 255))
        for x in range(10, 22):
            for y in range(10, 22):
                img.putpixel((x, y), (255, 255, 0))
        img.save(img_path, format="PNG")

        preset, confidence, reason, features = recommend_for_image(img_path)
        assert preset in {"pixel_art", "logo"}

    def test_returns_all_four_values(self, tmp_path: Path):
        img_path = tmp_path / "test.png"
        Image.new("RGB", (50, 50), color=(128, 128, 128)).save(img_path, format="PNG")
        result = recommend_for_image(img_path)
        assert len(result) == 4
