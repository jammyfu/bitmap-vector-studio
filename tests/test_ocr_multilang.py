from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from vector_studio.ai_ocr import (
    create_text_overlay_svg_multilang,
    detect_language,
    detect_vertical_text,
    preprocess_for_ocr,
    recognize_text_multilang,
)
from vector_studio.ocr_languages import (
    OCR_LANGUAGE_CONFIG,
    check_language_available,
    get_language_config,
    get_tesseract_languages,
    normalize_language_code,
    suggest_language_pack,
)


class TestDetectLanguage:
    def test_detects_chinese(self):
        assert detect_language("你好世界") == "zh"

    def test_detects_japanese(self):
        assert detect_language("こんにちは") == "ja"
        assert detect_language("カタカナ") == "ja"

    def test_detects_korean(self):
        assert detect_language("안녕하세요") == "ko"

    def test_detects_arabic(self):
        assert detect_language("مرحبا") == "ar"

    def test_detects_russian(self):
        assert detect_language("Привет") == "ru"

    def test_defaults_to_english(self):
        assert detect_language("Hello world") == "en"
        assert detect_language("") == "en"
        assert detect_language("12345") == "en"

    def test_chinese_priority_over_japanese(self):
        # Mixed Chinese + Japanese kana: Chinese should win
        assert detect_language("你好こんにちは") == "zh"


class TestRecognizeTextMultilang:
    def test_uses_provided_lang(self):
        img = Image.new("RGB", (100, 50), color=(255, 255, 255))
        mock_data = {
            "text": ["Hello"],
            "left": [10],
            "top": [10],
            "width": [30],
            "height": [20],
            "conf": [95],
        }
        fake_pytesseract = MagicMock()
        fake_pytesseract.image_to_data = MagicMock(return_value=mock_data)
        fake_pytesseract.Output = MagicMock(DICT=0)

        with patch.dict("sys.modules", {"pytesseract": fake_pytesseract}):
            with patch("vector_studio.ai_ocr.detect_text_regions", return_value=[]):
                result = recognize_text_multilang(img, lang="chi_sim")

        assert len(result) == 1
        assert result[0]["text"] == "Hello"
        assert result[0]["lang"] == "chi_sim"
        fake_pytesseract.image_to_data.assert_called_once()
        _, kwargs = fake_pytesseract.image_to_data.call_args
        assert kwargs.get("lang") == "chi_sim"

    def test_auto_detects_lang_from_regions(self):
        img = Image.new("RGB", (100, 50), color=(255, 255, 255))
        provided = [{"bbox": [10, 10, 30, 20], "confidence": 0.9, "text": "你好"}]
        mock_data = {
            "text": ["你好"],
            "left": [10],
            "top": [10],
            "width": [30],
            "height": [20],
            "conf": [95],
        }
        fake_pytesseract = MagicMock()
        fake_pytesseract.image_to_data = MagicMock(return_value=mock_data)
        fake_pytesseract.Output = MagicMock(DICT=0)

        with patch.dict("sys.modules", {"pytesseract": fake_pytesseract}):
            result = recognize_text_multilang(img, regions=provided, lang=None)

        assert len(result) == 1
        assert result[0]["lang"] == "chi_sim"

    def test_fallback_when_pytesseract_missing(self):
        img = Image.new("RGB", (50, 50), color=(128, 128, 128))
        provided = [{"bbox": [10, 10, 30, 20], "confidence": 0.9}]

        with patch.dict("sys.modules", {"pytesseract": None}):
            result = recognize_text_multilang(img, regions=provided, lang="eng")

        assert len(result) == 1
        assert result[0].get("lang") == "eng"


class TestDetectVerticalText:
    def test_detects_vertical_regions(self):
        # Create a tall narrow region with internal pattern (vertical text-like)
        img = Image.new("RGB", (40, 200), color=(255, 255, 255))
        for y in range(20, 180):
            for x in range(10, 30):
                # Checker-like pattern to create edges
                if ((x // 2) + (y // 4)) % 2 == 0:
                    img.putpixel((x, y), (0, 0, 0))

        regions = detect_vertical_text(img)
        assert isinstance(regions, list)
        # At least one region should be flagged vertical
        assert any(r.get("vertical") for r in regions)

    def test_no_vertical_in_horizontal_text(self):
        # Wide short region (horizontal text-like)
        img = Image.new("RGB", (200, 100), color=(255, 255, 255))
        for x in range(20, 180):
            for y in range(40, 60):
                img.putpixel((x, y), (0, 0, 0))

        regions = detect_vertical_text(img)
        # Should not flag horizontal regions as vertical
        assert not any(r.get("vertical") for r in regions)


class TestCreateTextOverlaySvgMultilang:
    def test_empty_regions_returns_empty(self):
        svg = create_text_overlay_svg_multilang([], svg_size=(100, 100))
        assert svg == ""

    def test_generates_multilang_text_elements(self):
        regions = [
            {"text": "Hello", "bbox": [10, 20, 50, 30], "lang": "eng"},
            {"text": "你好", "bbox": [70, 20, 50, 30], "lang": "chi_sim"},
        ]
        svg = create_text_overlay_svg_multilang(regions, svg_size=(200, 100))
        assert "<text" in svg
        assert "Hello" in svg
        assert "你好" in svg
        assert 'font-family="Noto Sans CJK SC' in svg

    def test_vertical_text_writing_mode(self):
        regions = [{"text": "縦書き", "bbox": [10, 10, 20, 80], "lang": "jpn", "vertical": True}]
        svg = create_text_overlay_svg_multilang(regions, svg_size=(100, 100))
        assert 'writing-mode="tb"' in svg

    def test_rtl_text_anchor(self):
        regions = [{"text": "مرحبا", "bbox": [10, 10, 50, 30], "lang": "ara"}]
        svg = create_text_overlay_svg_multilang(regions, svg_size=(100, 100))
        assert 'text-anchor="end"' in svg

    def test_escapes_xml_entities(self):
        regions = [{"text": "A & B <C>", "bbox": [10, 10, 200, 40], "lang": "eng"}]
        svg = create_text_overlay_svg_multilang(regions, svg_size=(300, 200))
        assert "&amp;" in svg
        assert "&lt;" in svg
        assert "&gt;" in svg
        assert "A & B <C>" not in svg


class TestPreprocessForOcr:
    def test_returns_rgb_image(self):
        img = Image.new("RGBA", (50, 50), color=(255, 0, 0, 128))
        result = preprocess_for_ocr(img, lang="eng")
        assert result.mode == "RGB"

    def test_sharpen_for_cjk(self):
        img = Image.new("RGB", (50, 50), color=(128, 128, 128))
        result_zh = preprocess_for_ocr(img, lang="chi_sim")
        result_jp = preprocess_for_ocr(img, lang="jpn")
        result_ko = preprocess_for_ocr(img, lang="kor")
        # All should return valid images
        assert result_zh.mode == "RGB"
        assert result_jp.mode == "RGB"
        assert result_ko.mode == "RGB"

    def test_standard_for_latin(self):
        img = Image.new("RGB", (50, 50), color=(128, 128, 128))
        result = preprocess_for_ocr(img, lang="eng")
        assert result.mode == "RGB"


class TestOcrLanguagesModule:
    def test_normalize_language_code(self):
        assert normalize_language_code("zh") == "chi_sim"
        assert normalize_language_code("ja") == "jpn"
        assert normalize_language_code("chi_sim") == "chi_sim"
        assert normalize_language_code(None) == "eng"
        assert normalize_language_code("") == "eng"

    def test_get_language_config(self):
        cfg = get_language_config("zh")
        assert cfg["tesseract_code"] == "chi_sim"
        assert "font_family" in cfg

    def test_get_language_config_fallback(self):
        cfg = get_language_config("unknown_lang")
        assert cfg["tesseract_code"] == "eng"

    def test_suggest_language_pack(self):
        hint = suggest_language_pack("chi_sim")
        assert "chi_sim" in hint
        assert "apt install" in hint or "brew install" in hint

    @patch("vector_studio.ocr_languages.subprocess.run")
    def test_get_tesseract_languages(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="List of languages:\neng\nchi_sim\n")
        langs = get_tesseract_languages()
        assert "eng" in langs
        assert "chi_sim" in langs

    @patch("vector_studio.ocr_languages.subprocess.run")
    def test_check_language_available(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="List of languages:\neng\n")
        assert check_language_available("eng") is True
        assert check_language_available("chi_sim") is False

    def test_ocr_language_config_completeness(self):
        required_keys = {"name", "tesseract_code", "font_family", "writing_mode", "preprocess", "direction"}
        for code, cfg in OCR_LANGUAGE_CONFIG.items():
            assert required_keys.issubset(set(cfg.keys())), f"{code} missing keys"
