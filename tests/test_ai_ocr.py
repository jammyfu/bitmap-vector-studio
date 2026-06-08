from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from vector_studio.ai_ocr import (
    create_text_overlay_svg,
    detect_text_regions,
    integrate_text_to_svg,
    recognize_text,
)


class TestDetectTextRegions:
    def test_empty_image_returns_empty(self):
        img = Image.new("RGB", (50, 50), color=(128, 128, 128))
        regions = detect_text_regions(img)
        assert isinstance(regions, list)
        # Uniform gray image has no text-like regions
        assert len(regions) == 0

    def test_detects_high_contrast_band(self):
        # Create a block pattern with both horizontal and vertical edges (like text)
        img = Image.new("RGB", (200, 100), color=(255, 255, 255))
        for x in range(20, 180):
            for y in range(30, 70):
                # Create a checker-like pattern inside the band
                if ((x // 8) + (y // 8)) % 2 == 0:
                    img.putpixel((x, y), (0, 0, 0))
        regions = detect_text_regions(img)
        assert isinstance(regions, list)
        # Should detect at least one wide, short region
        assert any(r["bbox"][2] > 50 and r["bbox"][3] < 50 for r in regions)

    def test_returns_bbox_and_confidence(self):
        img = Image.new("RGB", (200, 100), color=(0, 0, 0))
        for x in range(20, 180):
            for y in range(40, 60):
                img.putpixel((x, y), (255, 255, 255))
        regions = detect_text_regions(img)
        for region in regions:
            assert "bbox" in region
            assert "confidence" in region
            assert len(region["bbox"]) == 4
            assert 0.0 <= region["confidence"] <= 1.0

    def test_small_image_returns_empty(self):
        img = Image.new("RGB", (5, 5), color=(0, 0, 0))
        regions = detect_text_regions(img)
        assert regions == []

    def test_grayscale_input_accepted(self):
        img = Image.new("L", (100, 100), color=128)
        regions = detect_text_regions(img)
        assert isinstance(regions, list)


class TestRecognizeText:
    def test_returns_regions_when_no_ocr(self):
        img = Image.new("RGB", (200, 100), color=(0, 0, 0))
        for x in range(20, 180):
            for y in range(40, 60):
                img.putpixel((x, y), (255, 255, 255))
        regions = recognize_text(img)
        assert isinstance(regions, list)
        for region in regions:
            assert "text" in region
            assert "bbox" in region

    def test_uses_provided_regions(self):
        img = Image.new("RGB", (50, 50), color=(128, 128, 128))
        provided = [{"bbox": [10, 10, 30, 20], "confidence": 0.9}]
        result = recognize_text(img, regions=provided)
        assert len(result) == 1
        assert result[0]["bbox"] == [10, 10, 30, 20]

    def test_pytesseract_when_available(self):
        img = Image.new("RGB", (100, 50), color=(255, 255, 255))
        mock_data = {
            "text": ["Hello", "", "World"],
            "left": [10, 0, 50],
            "top": [10, 0, 10],
            "width": [30, 0, 40],
            "height": [20, 0, 20],
            "conf": [95, -1, 88],
        }
        fake_pytesseract = MagicMock()
        fake_pytesseract.image_to_data = MagicMock(return_value=mock_data)
        fake_pytesseract.Output = MagicMock(DICT=0)

        with patch.dict("sys.modules", {"pytesseract": fake_pytesseract}):
            with patch("vector_studio.ai_ocr.detect_text_regions", return_value=[]):
                result = recognize_text(img)

        assert len(result) == 2
        assert result[0]["text"] == "Hello"
        assert result[1]["text"] == "World"

    def test_easyocr_fallback(self):
        img = Image.new("RGB", (100, 50), color=(255, 255, 255))
        fake_reader = MagicMock()
        fake_reader.readtext = MagicMock(return_value=[
            ([[10, 10], [40, 10], [40, 30], [10, 30]], "Test", 0.92)
        ])
        fake_easyocr = MagicMock()
        fake_easyocr.Reader = MagicMock(return_value=fake_reader)

        with patch.dict("sys.modules", {"pytesseract": None, "easyocr": fake_easyocr}):
            with patch("vector_studio.ai_ocr._HAS_NUMPY", True):
                with patch("vector_studio.ai_ocr._to_numpy", return_value=MagicMock()):
                    result = recognize_text(img)

        assert len(result) == 1
        assert result[0]["text"] == "Test"


class TestCreateTextOverlaySvg:
    def test_empty_regions_returns_empty(self):
        svg = create_text_overlay_svg([], svg_size=(100, 100))
        assert svg == ""

    def test_generates_text_elements(self):
        regions = [
            {"text": "Hello", "bbox": [10, 20, 50, 30]},
            {"text": "World", "bbox": [70, 20, 50, 30]},
        ]
        svg = create_text_overlay_svg(regions, svg_size=(200, 100))
        assert "<text" in svg
        assert "Hello" in svg
        assert "World" in svg
        assert 'x="10"' in svg
        assert 'y="50"' in svg  # y + h = 20 + 30

    def test_escapes_xml_entities(self):
        regions = [{"text": "A & B <C>", "bbox": [10, 10, 200, 40]}]
        svg = create_text_overlay_svg(regions, svg_size=(300, 200))
        assert "&amp;" in svg
        assert "&lt;" in svg
        assert "&gt;" in svg
        assert "A & B <C>" not in svg

    def test_font_size_estimation(self):
        regions = [{"text": "Hi", "bbox": [0, 0, 100, 40]}]
        svg = create_text_overlay_svg(regions, svg_size=(200, 100))
        assert 'font-size="28"' in svg  # ~70% of 40


class TestIntegrateTextToSvg:
    def test_inserts_text_before_closing_svg(self, tmp_path: Path):
        svg_path = tmp_path / "test.svg"
        svg_path.write_text(
            '<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M0 0 L100 100" stroke="black"/>'
            "</svg>",
            encoding="utf-8",
        )
        regions = [{"text": "Hello", "bbox": [10, 10, 100, 40]}]
        out_path = tmp_path / "out.svg"
        result = integrate_text_to_svg(svg_path, regions, out_path)
        assert result == out_path
        text = out_path.read_text(encoding="utf-8")
        assert "<text" in text
        assert "Hello" in text
        assert "</svg>" in text

    def test_no_text_regions_copies_file(self, tmp_path: Path):
        svg_path = tmp_path / "test.svg"
        original = (
            '<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M0 0 L100 100" stroke="black"/>'
            "</svg>"
        )
        svg_path.write_text(original, encoding="utf-8")
        out_path = tmp_path / "out.svg"
        result = integrate_text_to_svg(svg_path, [], out_path)
        assert result == out_path
        assert out_path.read_text(encoding="utf-8") == original

    def test_malformed_svg_handled(self, tmp_path: Path):
        svg_path = tmp_path / "bad.svg"
        svg_path.write_text('<svg><path d="M0 0"/>', encoding="utf-8")
        regions = [{"text": "Hi", "bbox": [0, 0, 10, 10]}]
        out_path = tmp_path / "out.svg"
        result = integrate_text_to_svg(svg_path, regions, out_path)
        text = out_path.read_text(encoding="utf-8")
        assert "<text" in text
        assert "</svg>" in text
