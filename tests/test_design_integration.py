from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vector_studio.design_integration import DesignTokenSync, FigmaPlugin, SketchPlugin


class TestFigmaPlugin:
    def test_export_to_figma_missing_file(self):
        plugin = FigmaPlugin(token="fake")
        result = plugin.export_to_figma(Path("/nonexistent/file.svg"), "abc", "123")
        assert result is False

    def test_export_to_figma_success(self, tmp_path: Path):
        svg = tmp_path / "test.svg"
        svg.write_text("<svg></svg>")
        plugin = FigmaPlugin(token="fake")

        with patch.object(plugin, "_post_file", return_value={"id": "new-node"}):
            result = plugin.export_to_figma(svg, "abc", "123")
        assert result is True

    def test_import_from_figma(self, tmp_path: Path):
        plugin = FigmaPlugin(token="fake")
        fake_image_url = "http://example.com/fake.svg"
        fake_svg = b"<svg><rect/></svg>"

        class FakeResponse:
            def read(self):
                return fake_svg
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass

        with patch.object(plugin, "_request", return_value={"images": {"123": fake_image_url}}):
            with patch("urllib.request.urlopen", return_value=FakeResponse()):
                path = plugin.import_from_figma("abc", "123")

        assert path.exists()
        assert path.read_bytes() == fake_svg

    def test_sync_tokens(self):
        plugin = FigmaPlugin(token="fake")
        mock_data = {
            "meta": {
                "styles": [
                    {"name": "Primary", "style_type": "FILL", "node_id": "1:2"},
                    {"name": "Heading", "style_type": "TEXT", "node_id": "3:4"},
                ]
            }
        }

        with patch.object(plugin, "_request", return_value=mock_data):
            tokens = plugin.sync_tokens("abc")

        assert len(tokens["colors"]) == 1
        assert tokens["colors"][0]["name"] == "Primary"
        assert len(tokens["typography"]) == 1
        assert tokens["typography"][0]["name"] == "Heading"


class TestSketchPlugin:
    def test_export_to_sketch_missing_svg(self, tmp_path: Path):
        plugin = SketchPlugin()
        result = plugin.export_to_sketch(Path("/nonexistent.svg"), tmp_path / "doc.sketch")
        assert result is False

    def test_export_to_sketch_creates_document(self, tmp_path: Path):
        svg = tmp_path / "icon.svg"
        svg.write_text('<svg viewBox="0 0 10 10"><rect width="10" height="10"/></svg>')
        doc = tmp_path / "doc.sketch"
        plugin = SketchPlugin()
        result = plugin.export_to_sketch(svg, doc)
        assert result is True
        assert doc.exists()

    def test_import_from_sketch(self, tmp_path: Path):
        svg = tmp_path / "icon.svg"
        svg.write_text('<svg viewBox="0 0 10 10"><rect width="10" height="10"/></svg>')
        doc = tmp_path / "doc.sketch"
        plugin = SketchPlugin()
        plugin.export_to_sketch(svg, doc)

        out = plugin.import_from_sketch(doc, "icon")
        assert out.exists()
        assert "<svg" in out.read_text()

    def test_import_from_sketch_missing_layer(self, tmp_path: Path):
        doc = tmp_path / "doc.sketch"
        import zipfile

        with zipfile.ZipFile(doc, "w") as zf:
            zf.writestr("meta.json", "{}")

        plugin = SketchPlugin()
        with pytest.raises(RuntimeError, match="not found"):
            plugin.import_from_sketch(doc, "missing")


class TestDesignTokenSync:
    def test_extract_tokens(self, tmp_path: Path):
        svg = tmp_path / "sample.svg"
        svg.write_text(
            '<svg viewBox="0 0 100 100" width="100" height="100">'
            '<rect fill="#ff0000" stroke="rgb(0, 128, 0)"/>'
            '<text style="font-family: Arial;" x="10" y="20">Hello</text>'
            '</svg>'
        )
        sync = DesignTokenSync()
        tokens = sync.extract_tokens(svg)
        assert "#ff0000" in tokens["colors"]
        assert "#008000" in tokens["colors"]
        assert "Arial" in tokens["fonts"]
        assert any("width=100" in s for s in tokens["spacing"])

    def test_apply_tokens(self, tmp_path: Path):
        svg = tmp_path / "sample.svg"
        svg.write_text('<svg><rect fill="#ff0000"/></svg>')
        sync = DesignTokenSync()
        tokens = {"color_map": {"#ff0000": "#00ff00"}, "font_map": {}}
        sync.apply_tokens(svg, tokens)
        assert "#00ff00" in svg.read_text()
        assert "#ff0000" not in svg.read_text()

    def test_export_tokens_json(self, tmp_path: Path):
        sync = DesignTokenSync()
        tokens = {"colors": ["#ff0000"], "fonts": ["Arial"]}
        out = tmp_path / "tokens.json"
        sync.export_tokens_json(tokens, out)
        assert out.exists()
        data = out.read_text()
        assert "#ff0000" in data
        assert "Arial" in data
