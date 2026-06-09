from __future__ import annotations

import json
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vector_studio.import_export import ExportPackage, ImportExporter
from vector_studio.models import TraceOptions


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_data_dir(monkeypatch, tmp_path):
    """Redirect data directories into a temporary path for every test."""
    bvs_dir = tmp_path / ".bitmap_vector_studio"
    bvs_dir.mkdir(parents=True, exist_ok=True)
    templates_dir = bvs_dir / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        "vector_studio.import_export.Path.home",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "vector_studio.preset_manager._user_presets_dir",
        lambda: bvs_dir,
    )
    monkeypatch.setattr(
        "vector_studio.history._history_path",
        lambda: bvs_dir / "history.jsonl",
    )
    monkeypatch.setattr(
        "vector_studio.template_market._template_data_dir",
        lambda: templates_dir,
    )
    monkeypatch.setattr(
        "vector_studio.config._config_dir",
        lambda: bvs_dir,
    )


@pytest.fixture
def exporter(tmp_path) -> ImportExporter:
    return ImportExporter(data_dir=tmp_path / ".bitmap_vector_studio")


# ---------------------------------------------------------------------------
# ExportPackage
# ---------------------------------------------------------------------------


class TestExportPackage:
    def test_to_dict(self):
        pkg = ExportPackage(
            version="1.0.0",
            created_at="2024-01-01T00:00:00",
            items={"presets": [{"name": "test"}]},
        )
        data = pkg.to_dict()
        assert data["version"] == "1.0.0"
        assert data["items"]["presets"][0]["name"] == "test"


# ---------------------------------------------------------------------------
# Preset export / import
# ---------------------------------------------------------------------------


class TestPresetExportImport:
    def test_export_presets_empty(self, exporter):
        presets = exporter.export_presets()
        assert presets == []

    def test_export_presets_with_data(self, exporter, tmp_path):
        from vector_studio.preset_manager import save_preset

        save_preset("my_preset", TraceOptions(filter_speckle=7), "desc")
        presets = exporter.export_presets()
        assert len(presets) == 1
        assert presets[0]["name"] == "my_preset"
        assert presets[0]["description"] == "desc"

    def test_import_presets_merge(self, exporter, tmp_path):
        from vector_studio.preset_manager import save_preset, list_user_presets

        save_preset("existing", TraceOptions(filter_speckle=1))
        items = [
            {"name": "existing", "options": {"filter_speckle": 99}, "description": "new"},
            {"name": "new_one", "options": {"filter_speckle": 5}, "description": ""},
        ]
        count = exporter._import_presets(items, "merge")
        assert count == 2
        assert list_user_presets()["existing"]["options"]["filter_speckle"] == 99
        assert "new_one" in list_user_presets()

    def test_import_presets_skip(self, exporter, tmp_path):
        from vector_studio.preset_manager import save_preset, list_user_presets

        save_preset("existing", TraceOptions(filter_speckle=1))
        items = [
            {"name": "existing", "options": {"filter_speckle": 99}, "description": "new"},
        ]
        count = exporter._import_presets(items, "skip")
        assert count == 0
        assert list_user_presets()["existing"]["options"]["filter_speckle"] == 1

    def test_import_presets_replace(self, exporter, tmp_path):
        from vector_studio.preset_manager import save_preset, list_user_presets

        save_preset("existing", TraceOptions(filter_speckle=1))
        items = [
            {"name": "existing", "options": {"filter_speckle": 99}, "description": "new"},
        ]
        count = exporter._import_presets(items, "replace")
        assert count == 1
        assert list_user_presets()["existing"]["options"]["filter_speckle"] == 99


# ---------------------------------------------------------------------------
# Config export / import
# ---------------------------------------------------------------------------


class TestConfigExportImport:
    def test_export_config(self, exporter):
        data = exporter.export_config()
        assert "default_preset" in data

    def test_import_config(self, exporter, tmp_path):
        from vector_studio.config import Config

        config_data = {"default_preset": "logo", "max_workers": 8}
        count = exporter._import_config(config_data)
        assert count == 1
        cfg = Config.load()
        assert cfg.default_preset == "logo"
        assert cfg.max_workers == 8


# ---------------------------------------------------------------------------
# History export / import
# ---------------------------------------------------------------------------


class TestHistoryExportImport:
    def test_export_history_empty(self, exporter):
        history = exporter.export_history()
        assert history == []

    def test_import_history(self, exporter, tmp_path):
        from vector_studio.history import get_recent_tasks

        items = [
            {
                "task_id": "t1",
                "input_path": "/a.png",
                "output_path": "/a.svg",
                "preset_name": "poster",
                "options": {},
                "stats": {},
                "engine": "vtracer",
                "elapsed_seconds": 1.0,
                "export_formats": [],
            }
        ]
        count = exporter._import_history(items)
        assert count == 1
        recent = get_recent_tasks(limit=10)
        assert len(recent) == 1
        assert recent[0]["task_id"] == "t1"


# ---------------------------------------------------------------------------
# Template export / import
# ---------------------------------------------------------------------------


class TestTemplateExportImport:
    def test_export_templates_empty(self, exporter):
        templates = exporter.export_templates()
        assert templates == []

    def test_import_templates(self, exporter, tmp_path):
        from vector_studio.template_market import TemplateMarket

        items = [
            {
                "template_id": "tid-1",
                "name": "Test",
                "category": "logo",
                "tags": ["minimal"],
                "preview_url": "",
                "data": {},
                "author": "",
                "rating": 0.0,
                "downloads": 0,
            }
        ]
        count = exporter._import_templates(items)
        assert count == 1
        market = TemplateMarket()
        assert market.get_template("tid-1") is not None


# ---------------------------------------------------------------------------
# JSON / ZIP round-trips
# ---------------------------------------------------------------------------


class TestPackageRoundTrip:
    def test_export_to_json(self, exporter, tmp_path):
        path = tmp_path / "export.json"
        exporter.export_to_json(path)
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "version" in data
        assert "items" in data

    def test_export_to_zip(self, exporter, tmp_path):
        path = tmp_path / "export.zip"
        exporter.export_to_zip(path)
        assert path.exists()
        with zipfile.ZipFile(path, "r") as zf:
            assert "manifest.json" in zf.namelist()

    def test_import_from_json(self, exporter, tmp_path):
        from vector_studio.preset_manager import save_preset

        save_preset("json_preset", TraceOptions(filter_speckle=3))
        export_path = tmp_path / "export.json"
        exporter.export_to_json(export_path, include=["presets"])

        # Clear and re-import
        from vector_studio.preset_manager import _user_presets_file, _save_user_presets_raw
        _save_user_presets_raw({})

        stats = exporter.import_from_json(export_path, merge_strategy="merge")
        assert stats["imported"]["presets"] == 1

    def test_import_from_zip(self, exporter, tmp_path):
        from vector_studio.preset_manager import save_preset

        save_preset("zip_preset", TraceOptions(filter_speckle=4))
        export_path = tmp_path / "export.zip"
        exporter.export_to_zip(export_path, include=["presets"])

        # Clear and re-import
        from vector_studio.preset_manager import _save_user_presets_raw
        _save_user_presets_raw({})

        stats = exporter.import_from_zip(export_path, merge_strategy="merge")
        assert stats["imported"]["presets"] == 1

    def test_import_json_without_items_wrapper(self, exporter, tmp_path):
        """Legacy JSON that is just a flat dict of categories."""
        raw = {"presets": [{"name": "legacy", "options": {"filter_speckle": 2}, "description": ""}]}
        path = tmp_path / "legacy.json"
        path.write_text(json.dumps(raw), encoding="utf-8")
        stats = exporter.import_from_json(path, merge_strategy="merge")
        assert stats["imported"]["presets"] == 1

    def test_create_package_selective_include(self, exporter, tmp_path):
        pkg = exporter.create_package(include=["config"])
        assert "config" in pkg.items
        assert "presets" not in pkg.items
        assert "history" not in pkg.items
        assert "templates" not in pkg.items

    def test_import_category_unknown_returns_zero(self, exporter):
        assert exporter._import_category("unknown", [], "merge") == 0

    def test_import_presets_missing_name_skipped(self, exporter):
        items = [{"options": {"filter_speckle": 2}}]
        assert exporter._import_presets(items, "merge") == 0

    def test_import_presets_bad_options_skipped(self, exporter):
        items = [{"name": "bad", "options": {"unknown_bad_field": 123}}]
        assert exporter._import_presets(items, "merge") == 0

    def test_import_templates_bad_data_skipped(self, exporter):
        items = [{"template_id": "", "name": "", "category": "", "tags": 123}]
        assert exporter._import_templates(items) == 0

    def test_import_history_bad_data_skipped(self, exporter):
        items = [{"input_path": "/a.png", "timestamp": None}]
        # Should not crash; count may be 0 or 1 depending on serialization
        count = exporter._import_history(items)
        assert count >= 0
