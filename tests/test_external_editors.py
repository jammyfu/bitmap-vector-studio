"""Tests for external editor detection and opening utilities."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vector_studio.external_editors import (
    EditorInfo,
    EditorNotFoundError,
    EditorOpenError,
    detect_editors,
    get_default_editor,
    open_with_default_editor,
    open_with_editor,
)


class TestEditorInfo:
    def test_editor_info_repr_available(self):
        info = EditorInfo(name="inkscape", display_name="Inkscape", executable_path=Path("/usr/bin/inkscape"), platform="linux", is_available=True)
        assert "available" in repr(info)

    def test_editor_info_repr_not_found(self):
        info = EditorInfo(name="illustrator", display_name="Adobe Illustrator", executable_path=None, platform="windows", is_available=False)
        assert "not found" in repr(info)


class TestDetectEditors:
    @patch("vector_studio.external_editors._current_platform", return_value="linux")
    @patch("vector_studio.external_editors.shutil.which", return_value="/usr/bin/inkscape")
    @patch("vector_studio.external_editors.Path.exists", return_value=True)
    def test_detect_editors_finds_inkscape_on_linux(self, mock_exists, mock_which, mock_platform):
        editors = detect_editors()
        inkscape = next(e for e in editors if e.name == "inkscape")
        assert inkscape.is_available
        assert inkscape.executable_path == Path("/usr/bin/inkscape")

    @patch("vector_studio.external_editors._current_platform", return_value="windows")
    @patch("vector_studio.external_editors._resolve_windows_path_candidates", return_value=[])
    @patch("vector_studio.external_editors._winreg_read_install_path", return_value=None)
    @patch("vector_studio.external_editors.shutil.which", return_value=None)
    def test_detect_editors_returns_not_available_when_missing(self, mock_which, mock_reg, mock_candidates, mock_platform):
        editors = detect_editors()
        illustrator = next(e for e in editors if e.name == "illustrator")
        assert not illustrator.is_available
        assert illustrator.executable_path is None

    def test_detect_editors_finds_affinity_on_macos(self, monkeypatch):
        monkeypatch.setattr("vector_studio.external_editors._current_platform", lambda: "macos")
        monkeypatch.setattr("vector_studio.external_editors.MACOS_COMMON_PATHS", {"affinity_designer": [Path("/Applications/Affinity Designer 2.app")]})
        monkeypatch.setattr("vector_studio.external_editors.Path.exists", lambda self: True)
        editors = detect_editors()
        affinity = next(e for e in editors if e.name == "affinity_designer")
        assert affinity.is_available
        assert affinity.executable_path == Path("/Applications/Affinity Designer 2.app")


class TestGetDefaultEditor:
    @patch("vector_studio.external_editors.detect_editors")
    def test_get_default_editor_returns_first_available(self, mock_detect):
        mock_detect.return_value = [
            EditorInfo(name="illustrator", display_name="Adobe Illustrator", executable_path=None, platform="windows", is_available=False),
            EditorInfo(name="inkscape", display_name="Inkscape", executable_path=Path("/usr/bin/inkscape"), platform="linux", is_available=True),
        ]
        result = get_default_editor()
        assert result is not None
        assert result.name == "inkscape"

    @patch("vector_studio.external_editors.detect_editors", return_value=[])
    def test_get_default_editor_returns_none_when_empty(self, mock_detect):
        result = get_default_editor()
        assert result is None


class TestOpenWithEditor:
    def test_open_with_editor_raises_for_missing_svg(self):
        with pytest.raises(FileNotFoundError):
            open_with_editor(Path("/nonexistent/file.svg"), "inkscape")

    @patch("vector_studio.external_editors._current_platform", return_value="linux")
    @patch("vector_studio.external_editors.detect_editors")
    @patch("vector_studio.external_editors.subprocess.Popen")
    @patch("vector_studio.external_editors.Path.exists", return_value=True)
    def test_open_with_editor_invokes_popen_for_inkscape(self, mock_exists, mock_popen, mock_detect, mock_platform, tmp_path: Path):
        svg = tmp_path / "test.svg"
        svg.write_text("<svg></svg>")
        mock_detect.return_value = [
            EditorInfo(name="inkscape", display_name="Inkscape", executable_path=Path("/usr/bin/inkscape"), platform="linux", is_available=True),
        ]
        open_with_editor(svg, "inkscape")
        mock_popen.assert_called_once_with([str(Path("/usr/bin/inkscape")), str(svg)], shell=False)

    @patch("vector_studio.external_editors._current_platform", return_value="windows")
    @patch("vector_studio.external_editors.os.startfile")
    @patch("vector_studio.external_editors.detect_editors")
    def test_open_with_editor_uses_startfile_for_default_on_windows(self, mock_detect, mock_startfile, mock_platform, tmp_path: Path):
        svg = tmp_path / "test.svg"
        svg.write_text("<svg></svg>")
        mock_detect.return_value = []
        open_with_editor(svg, None)
        mock_startfile.assert_called_once_with(str(svg))

    @patch("vector_studio.external_editors._current_platform", return_value="macos")
    @patch("vector_studio.external_editors.subprocess.Popen")
    @patch("vector_studio.external_editors.detect_editors")
    def test_open_with_editor_uses_open_for_default_on_macos(self, mock_detect, mock_popen, mock_platform, tmp_path: Path):
        svg = tmp_path / "test.svg"
        svg.write_text("<svg></svg>")
        mock_detect.return_value = []
        open_with_editor(svg, None)
        mock_popen.assert_called_once_with(["open", str(svg)], shell=False)

    @patch("vector_studio.external_editors._current_platform", return_value="linux")
    @patch("vector_studio.external_editors.subprocess.Popen")
    @patch("vector_studio.external_editors.detect_editors")
    def test_open_with_editor_uses_xdg_open_for_default_on_linux(self, mock_detect, mock_popen, mock_platform, tmp_path: Path):
        svg = tmp_path / "test.svg"
        svg.write_text("<svg></svg>")
        mock_detect.return_value = []
        open_with_editor(svg, None)
        mock_popen.assert_called_once_with(["xdg-open", str(svg)], shell=False)

    @patch("vector_studio.external_editors._current_platform", return_value="linux")
    @patch("vector_studio.external_editors.detect_editors", return_value=[])
    def test_open_with_editor_raises_not_found_for_missing_editor(self, mock_detect, mock_platform, tmp_path: Path):
        svg = tmp_path / "test.svg"
        svg.write_text("<svg></svg>")
        with pytest.raises(EditorNotFoundError) as exc_info:
            open_with_editor(svg, "illustrator")
        assert "illustrator" in str(exc_info.value)

    @patch("vector_studio.external_editors._current_platform", return_value="linux")
    @patch("vector_studio.external_editors.subprocess.Popen", side_effect=OSError("boom"))
    @patch("vector_studio.external_editors.detect_editors")
    @patch("vector_studio.external_editors.Path.exists", return_value=True)
    def test_open_with_editor_raises_open_error_on_failure(self, mock_exists, mock_detect, mock_popen, mock_platform, tmp_path: Path):
        svg = tmp_path / "test.svg"
        svg.write_text("<svg></svg>")
        mock_detect.return_value = [
            EditorInfo(name="inkscape", display_name="Inkscape", executable_path=Path("/usr/bin/inkscape"), platform="linux", is_available=True),
        ]
        with pytest.raises(EditorOpenError) as exc_info:
            open_with_editor(svg, "inkscape")
        assert "boom" in str(exc_info.value)


class TestOpenWithDefaultEditor:
    @patch("vector_studio.external_editors.get_default_editor")
    @patch("vector_studio.external_editors.open_with_editor")
    def test_open_with_default_editor_delegates_when_editor_found(self, mock_open, mock_get_default, tmp_path: Path):
        svg = tmp_path / "test.svg"
        svg.write_text("<svg></svg>")
        mock_editor = MagicMock()
        mock_editor.name = "inkscape"
        mock_get_default.return_value = mock_editor
        open_with_default_editor(svg)
        mock_open.assert_called_once_with(svg, "inkscape")

    @patch("vector_studio.external_editors.get_default_editor", return_value=None)
    @patch("vector_studio.external_editors.open_with_editor")
    def test_open_with_default_editor_falls_back_to_system_default(self, mock_open, mock_get_default, tmp_path: Path):
        svg = tmp_path / "test.svg"
        svg.write_text("<svg></svg>")
        open_with_default_editor(svg)
        mock_open.assert_called_once_with(svg, None)
