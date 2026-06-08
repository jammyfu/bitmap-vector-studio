import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from vector_studio.cli import app
from vector_studio.template_market import (
    Template,
    TemplateEditor,
    TemplateMarket,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# Template dataclass
# ---------------------------------------------------------------------------


class TestTemplate:
    def test_template_fields(self):
        """Template dataclass stores all expected fields."""
        t = Template(
            template_id="t1",
            name="Logo Template",
            category="logo",
            tags=["vector", "minimal"],
            preview_url="http://example.com/preview.svg",
            data={"preset": "logo"},
            author="alice",
            rating=4.5,
            downloads=120,
        )
        assert t.template_id == "t1"
        assert t.name == "Logo Template"
        assert t.category == "logo"
        assert t.tags == ["vector", "minimal"]
        assert t.rating == 4.5
        assert t.downloads == 120

    def test_serialization_roundtrip(self):
        """to_dict / from_dict preserves template state."""
        t = Template(
            template_id="t2",
            name="Photo Template",
            category="photo",
            tags=["gradient"],
            data={"preset": "photo"},
            author="bob",
            rating=3.0,
            downloads=50,
        )
        data = t.to_dict()
        restored = Template.from_dict(data)
        assert restored.template_id == t.template_id
        assert restored.name == t.name
        assert restored.rating == t.rating
        assert restored.tags == t.tags


# ---------------------------------------------------------------------------
# TemplateMarket
# ---------------------------------------------------------------------------


class TestTemplateMarket:
    def test_discover_templates_empty(self, tmp_path, monkeypatch):
        """discover_templates returns an empty list when no templates exist."""
        monkeypatch.setattr(
            "vector_studio.template_market._template_data_dir", lambda: tmp_path
        )
        market = TemplateMarket()
        assert market.discover_templates() == []

    def test_publish_and_discover(self, tmp_path, monkeypatch):
        """Publishing a template makes it discoverable."""
        monkeypatch.setattr(
            "vector_studio.template_market._template_data_dir", lambda: tmp_path
        )
        market = TemplateMarket()
        t = Template(
            template_id="",
            name="Icon Pack",
            category="icon",
            tags=["flat", "color"],
            data={"preset": "logo"},
        )
        tid = market.publish_template(t, "alice")
        assert tid
        results = market.discover_templates()
        assert len(results) == 1
        assert results[0].name == "Icon Pack"

    def test_discover_with_query_and_category(self, tmp_path, monkeypatch):
        """Query and category filters work correctly."""
        monkeypatch.setattr(
            "vector_studio.template_market._template_data_dir", lambda: tmp_path
        )
        market = TemplateMarket()
        market.publish_template(
            Template(template_id="", name="Logo A", category="logo", tags=["minimal"], data={}),
            "u1",
        )
        market.publish_template(
            Template(template_id="", name="Photo A", category="photo", tags=["landscape"], data={}),
            "u2",
        )
        assert len(market.discover_templates(category="logo")) == 1
        assert len(market.discover_templates(query="photo")) == 1
        assert len(market.discover_templates(query="nonexistent")) == 0

    def test_rate_template(self, tmp_path, monkeypatch):
        """rate_template updates the average rating."""
        monkeypatch.setattr(
            "vector_studio.template_market._template_data_dir", lambda: tmp_path
        )
        market = TemplateMarket()
        t = Template(template_id="", name="R", category="c", data={})
        tid = market.publish_template(t, "u1")
        assert market.rate_template(tid, "u1", 4) is True
        assert market.rate_template(tid, "u2", 2) is True
        updated = market.get_template(tid)
        assert updated is not None
        assert updated.rating == 3.0

    def test_rate_template_out_of_range(self, tmp_path, monkeypatch):
        """rate_template rejects ratings outside 1–5."""
        monkeypatch.setattr(
            "vector_studio.template_market._template_data_dir", lambda: tmp_path
        )
        market = TemplateMarket()
        with pytest.raises(ValueError, match="Rating must be between 1 and 5"):
            market.rate_template("any", "u1", 0)
        with pytest.raises(ValueError, match="Rating must be between 1 and 5"):
            market.rate_template("any", "u1", 6)

    def test_get_recommendations(self, tmp_path, monkeypatch):
        """get_recommendations scores templates by context match."""
        monkeypatch.setattr(
            "vector_studio.template_market._template_data_dir", lambda: tmp_path
        )
        market = TemplateMarket()
        market.publish_template(
            Template(template_id="", name="Logo Rec", category="logo", tags=["logo", "minimal"], data={}),
            "u1",
        )
        market.publish_template(
            Template(template_id="", name="Photo Rec", category="photo", tags=["photo"], data={}),
            "u2",
        )
        recs = market.get_recommendations("user", {"image_type": "logo", "category": "logo"})
        assert recs[0].name == "Logo Rec"

    def test_apply_template_not_found(self, tmp_path, monkeypatch):
        """apply_template raises ValueError for missing template."""
        monkeypatch.setattr(
            "vector_studio.template_market._template_data_dir", lambda: tmp_path
        )
        market = TemplateMarket()
        with pytest.raises(ValueError, match="not found"):
            market.apply_template("missing", tmp_path / "in.png", tmp_path / "out.svg")


# ---------------------------------------------------------------------------
# TemplateEditor
# ---------------------------------------------------------------------------


class TestTemplateEditor:
    def test_load_and_save_template(self, tmp_path):
        """load_template and save_template round-trip correctly."""
        editor = TemplateEditor()
        data = {
            "template_id": "t3",
            "name": "Test",
            "category": "test",
            "tags": [],
            "data": {},
        }
        path = tmp_path / "template.json"
        editor.save_template(data, path)
        loaded = editor.load_template(path)
        assert loaded["template_id"] == "t3"
        assert loaded["name"] == "Test"

    def test_edit_template(self):
        """edit_template merges changes and adds updated_at."""
        editor = TemplateEditor()
        original = {"name": "Old", "data": {"preset": "poster"}, "tags": ["a"]}
        changes = {"name": "New", "data": {"optimize": True}}
        updated = editor.edit_template(original, changes)
        assert updated["name"] == "New"
        assert updated["data"] == {"preset": "poster", "optimize": True}
        assert "updated_at" in updated

    def test_load_missing_file(self, tmp_path):
        """load_template raises FileNotFoundError for missing files."""
        editor = TemplateEditor()
        with pytest.raises(FileNotFoundError):
            editor.load_template(tmp_path / "missing.json")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestTemplateCLI:
    def test_template_list_empty(self, tmp_path, monkeypatch):
        """template list prints a friendly message when empty."""
        monkeypatch.setattr(
            "vector_studio.template_market._template_data_dir", lambda: tmp_path
        )
        result = runner.invoke(app, ["template", "list"])
        assert result.exit_code == 0
        assert "No templates found" in result.output

    def test_template_list_with_items(self, tmp_path, monkeypatch):
        """template list renders a table of templates."""
        monkeypatch.setattr(
            "vector_studio.template_market._template_data_dir", lambda: tmp_path
        )
        market = TemplateMarket()
        market.publish_template(
            Template(template_id="", name="T1", category="logo", data={}),
            "u1",
        )
        result = runner.invoke(app, ["template", "list"])
        assert result.exit_code == 0
        assert "T1" in result.output

    def test_template_recommend(self, tmp_path, monkeypatch):
        """template recommend renders recommendations."""
        monkeypatch.setattr(
            "vector_studio.template_market._template_data_dir", lambda: tmp_path
        )
        market = TemplateMarket()
        market.publish_template(
            Template(template_id="", name="Rec", category="logo", tags=["logo"], data={}),
            "u1",
        )
        result = runner.invoke(app, ["template", "recommend", "--image-type", "logo"])
        assert result.exit_code == 0
        assert "Rec" in result.output

    def test_template_publish(self, tmp_path, monkeypatch):
        """template publish uploads a template JSON file."""
        monkeypatch.setattr(
            "vector_studio.template_market._template_data_dir", lambda: tmp_path
        )
        template_file = tmp_path / "my_template.json"
        template_file.write_text(
            json.dumps(
                {
                    "template_id": "",
                    "name": "Pub",
                    "category": "icon",
                    "tags": [],
                    "data": {"preset": "logo"},
                }
            ),
            encoding="utf-8",
        )
        result = runner.invoke(app, ["template", "publish", str(template_file)])
        assert result.exit_code == 0
        assert "Published template" in result.output

    def test_template_publish_invalid_json(self, tmp_path, monkeypatch):
        """template publish exits with code 1 for invalid JSON."""
        monkeypatch.setattr(
            "vector_studio.template_market._template_data_dir", lambda: tmp_path
        )
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json", encoding="utf-8")
        result = runner.invoke(app, ["template", "publish", str(bad_file)])
        assert result.exit_code == 1
        assert "Invalid template file" in result.output

    def test_template_apply(self, tmp_path, monkeypatch):
        """template apply invokes trace_image and prints success."""
        monkeypatch.setattr(
            "vector_studio.template_market._template_data_dir", lambda: tmp_path
        )
        img = tmp_path / "img.png"
        img.write_bytes(b"fake image")
        out = tmp_path / "out.svg"
        out.write_text("<svg></svg>")

        market = TemplateMarket()
        tid = market.publish_template(
            Template(template_id="", name="App", category="logo", data={"preset": "logo"}),
            "u1",
        )

        mock_result = MagicMock()
        mock_result.svg_path = out

        with patch("vector_studio.template_market.trace_image", return_value=mock_result):
            result = runner.invoke(app, ["template", "apply", tid, str(img), "--output", str(out)])
        assert result.exit_code == 0
        assert "Applied template" in result.output
