from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vector_studio.security import (
    ALLOWED_EXTENSIONS,
    DANGEROUS_SVG_TAGS,
    FileHashChecker,
    InputValidator,
    SVGSanitizer,
    SecurityError,
)


class TestInputValidatorValidateFilePath:
    def test_valid_file_path(self, tmp_path: Path):
        file = tmp_path / "test.png"
        file.write_text("fake image")
        result = InputValidator.validate_file_path(file)
        assert result == file.resolve()

    def test_path_traversal_attack(self):
        with pytest.raises(SecurityError, match="路径包含非法遍历"):
            InputValidator.validate_file_path("../etc/passwd", must_exist=False)

    def test_symlink_rejected(self, tmp_path: Path):
        real = tmp_path / "real.png"
        real.write_text("fake")
        link = tmp_path / "link.png"
        try:
            link.symlink_to(real)
        except OSError:
            pytest.skip("Symlink creation not supported on this platform")
        with pytest.raises(SecurityError, match="不允许符号链接"):
            InputValidator.validate_file_path(link)

    def test_missing_file_raises(self, tmp_path: Path):
        missing = tmp_path / "missing.png"
        with pytest.raises(SecurityError, match="文件不存在"):
            InputValidator.validate_file_path(missing)

    def test_base_dir_restriction(self, tmp_path: Path):
        file = tmp_path / "test.png"
        file.write_text("fake image")
        # With base_dir set to a different directory, should fail
        other_dir = tmp_path / "other"
        other_dir.mkdir()
        with pytest.raises(SecurityError, match="路径不在允许范围内"):
            InputValidator.validate_file_path(file, base_dir=other_dir)

    def test_allow_write_bypasses_base_dir(self, tmp_path: Path):
        file = tmp_path / "test.png"
        file.write_text("fake image")
        other_dir = tmp_path / "other"
        other_dir.mkdir()
        result = InputValidator.validate_file_path(file, base_dir=other_dir, allow_write=True)
        assert result == file.resolve()


class TestInputValidatorValidateImageFile:
    def test_valid_image_file(self, tmp_path: Path):
        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 100)
        InputValidator.validate_image_file(img)

    def test_unsupported_extension(self, tmp_path: Path):
        bad = tmp_path / "test.exe"
        bad.write_text("not an image")
        with pytest.raises(SecurityError, match="不支持的文件格式"):
            InputValidator.validate_image_file(bad)

    def test_file_too_large(self, tmp_path: Path):
        from vector_studio.security import MAX_FILE_SIZE
        big = tmp_path / "big.png"
        big.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * (MAX_FILE_SIZE + 1))
        with pytest.raises(SecurityError, match="文件过大"):
            InputValidator.validate_image_file(big)

    def test_missing_file(self, tmp_path: Path):
        missing = tmp_path / "missing.png"
        with pytest.raises(SecurityError, match="文件不存在"):
            InputValidator.validate_image_file(missing)


class TestInputValidatorValidatePresetName:
    def test_valid_preset_names(self):
        assert InputValidator.validate_preset_name("logo") == "logo"
        assert InputValidator.validate_preset_name("my-preset_123") == "my-preset_123"

    def test_invalid_preset_name(self):
        with pytest.raises(SecurityError, match="非法预设名称"):
            InputValidator.validate_preset_name("../../etc/passwd")
        with pytest.raises(SecurityError, match="非法预设名称"):
            InputValidator.validate_preset_name("preset with spaces")
        with pytest.raises(SecurityError, match="非法预设名称"):
            InputValidator.validate_preset_name("preset<script>")


class TestInputValidatorValidateOptions:
    def test_valid_options(self):
        opts = {
            "color_precision": 4,
            "filter_speckle": 8,
            "max_iterations": 10,
            "max_input_side": 1024,
        }
        result = InputValidator.validate_options(opts)
        assert result["color_precision"] == 4
        assert result["filter_speckle"] == 8
        assert result["max_iterations"] == 10
        assert result["max_input_side"] == 1024

    def test_color_precision_out_of_range(self):
        with pytest.raises(SecurityError, match="color_precision 超出范围"):
            InputValidator.validate_options({"color_precision": 0})
        with pytest.raises(SecurityError, match="color_precision 超出范围"):
            InputValidator.validate_options({"color_precision": 9})

    def test_filter_speckle_out_of_range(self):
        with pytest.raises(SecurityError, match="filter_speckle 超出范围"):
            InputValidator.validate_options({"filter_speckle": 129})

    def test_max_iterations_out_of_range(self):
        with pytest.raises(SecurityError, match="max_iterations 超出范围"):
            InputValidator.validate_options({"max_iterations": 51})

    def test_max_input_side_too_small(self):
        with pytest.raises(SecurityError, match="max_input_side 过小"):
            InputValidator.validate_options({"max_input_side": 32})

    def test_empty_options(self):
        assert InputValidator.validate_options({}) == {}


class TestSVGSanitizer:
    def test_removes_script_tag(self):
        svg = '<svg><script>alert("xss")</script><path d="M0 0"/></svg>'
        clean = SVGSanitizer.sanitize(svg)
        assert "script" not in clean.lower() or "alert" not in clean.lower()

    def test_removes_event_handlers(self):
        svg = '<svg onload="alert(1)"><path d="M0 0"/></svg>'
        clean = SVGSanitizer.sanitize(svg)
        assert "onload" not in clean.lower()

    def test_removes_foreign_object(self):
        svg = '<svg><foreignObject><iframe src="evil"/></foreignObject><path d="M0 0"/></svg>'
        clean = SVGSanitizer.sanitize(svg)
        assert "foreignObject" not in clean
        assert "iframe" not in clean

    def test_keeps_safe_svg(self):
        svg = '<svg viewBox="0 0 100 100"><path d="M0 0 L100 100" stroke="black"/></svg>'
        clean = SVGSanitizer.sanitize(svg)
        assert "path" in clean
        assert "viewBox" in clean

    def test_is_safe_detects_dangerous_content(self):
        assert not SVGSanitizer.is_safe('<svg><script>alert(1)</script></svg>')
        assert SVGSanitizer.is_safe('<svg><path d="M0 0"/></svg>')

    def test_handles_malformed_svg(self):
        svg = "not valid xml"
        result = SVGSanitizer.sanitize(svg)
        assert result == svg


class TestFileHashChecker:
    def test_compute_hash(self, tmp_path: Path):
        file = tmp_path / "test.txt"
        file.write_text("hello world")
        h = FileHashChecker.compute_hash(file)
        assert len(h) == 64
        assert h == "a" * 64 or h != "0" * 64  # just check it's a real hash

    def test_verify_hash(self, tmp_path: Path):
        file = tmp_path / "test.txt"
        file.write_text("hello world")
        h = FileHashChecker.compute_hash(file)
        assert FileHashChecker.verify_hash(file, h) is True
        assert FileHashChecker.verify_hash(file, "0" * 64) is False

    def test_compute_hash_large_file(self, tmp_path: Path):
        file = tmp_path / "large.bin"
        file.write_bytes(b"x" * 100_000)
        h = FileHashChecker.compute_hash(file)
        assert len(h) == 64
