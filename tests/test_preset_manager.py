import json
from pathlib import Path

import pytest

from vector_studio.models import TraceOptions
from vector_studio import preset_manager as pm
from vector_studio.presets import PRESETS


@pytest.fixture(autouse=True)
def _isolated_user_store(monkeypatch, tmp_path):
    """Redirect the user presets file into a temporary directory for every test."""
    store = tmp_path / "presets.json"
    monkeypatch.setattr(pm, "_user_presets_file", lambda: store)
    # Ensure a clean slate even if a previous test left something behind.
    store.unlink(missing_ok=True)


class TestSaveAndLoad:
    def test_save_and_load_roundtrip(self):
        opts = TraceOptions(colormode="binary", filter_speckle=8)
        pm.save_preset("scan_test", opts, description="test desc")
        loaded = pm.load_preset("scan_test")
        assert loaded == opts

    def test_load_normalizes_name(self):
        opts = TraceOptions(mode="pixel")
        pm.save_preset("pixel-art", opts)
        assert pm.load_preset("pixel art") == opts
        assert pm.load_preset("pixel_art") == opts
        assert pm.load_preset("Pixel-Art") == opts

    def test_save_replaces_existing(self):
        pm.save_preset("dup", TraceOptions(filter_speckle=1))
        pm.save_preset("dup", TraceOptions(filter_speckle=99))
        assert pm.load_preset("dup").filter_speckle == 99

    def test_save_non_traceoptions_raises(self):
        with pytest.raises(TypeError):
            pm.save_preset("bad", {"colormode": "binary"})  # type: ignore[arg-type]


class TestDelete:
    def test_delete_removes_user_preset(self):
        pm.save_preset("to_delete", TraceOptions())
        assert pm.preset_exists("to_delete")
        pm.delete_preset("to_delete")
        assert not pm.preset_exists("to_delete")

    def test_delete_builtin_is_noop(self):
        assert pm.preset_exists("bw")
        pm.delete_preset("bw")
        assert pm.preset_exists("bw")


class TestListAndExists:
    def test_list_user_presets_empty(self):
        assert pm.list_user_presets() == {}

    def test_list_user_presets_structure(self):
        pm.save_preset("listed", TraceOptions(), "a description")
        presets = pm.list_user_presets()
        assert "listed" in presets
        assert presets["listed"]["description"] == "a description"
        assert "created_at" in presets["listed"]
        assert "options" in presets["listed"]

    def test_preset_exists_builtin(self):
        assert pm.preset_exists("bw")
        assert pm.preset_exists("poster")
        assert not pm.preset_exists("nonexistent")

    def test_preset_exists_user(self):
        pm.save_preset("user_one", TraceOptions())
        assert pm.preset_exists("user_one")


class TestMerge:
    def test_get_all_presets_includes_builtins(self):
        all_presets = pm.get_all_presets()
        for key in PRESETS:
            assert key in all_presets

    def test_get_all_presets_includes_user(self):
        pm.save_preset("custom_user", TraceOptions(filter_speckle=77))
        all_presets = pm.get_all_presets()
        assert all_presets["custom_user"].filter_speckle == 77

    def test_user_preset_overrides_builtin(self):
        original = PRESETS["bw"]
        override = TraceOptions(colormode="color", filter_speckle=42)
        pm.save_preset("bw", override)
        merged = pm.get_all_presets()
        assert merged["bw"].colormode == "color"
        assert merged["bw"].filter_speckle == 42
        # Built-in dict itself must remain untouched.
        assert PRESETS["bw"] == original


class TestExportImport:
    def test_export_presets_roundtrip(self, tmp_path: Path):
        pm.save_preset("exp1", TraceOptions(filter_speckle=1), "first")
        pm.save_preset("exp2", TraceOptions(filter_speckle=2), "second")
        export_file = tmp_path / "exported.json"
        pm.export_presets(export_file)
        assert export_file.exists()
        data = json.loads(export_file.read_text(encoding="utf-8"))
        assert set(data.keys()) == {"exp1", "exp2"}

    def test_import_presets_without_overwrite(self, tmp_path: Path):
        pm.save_preset("imp", TraceOptions(filter_speckle=1))
        export_file = tmp_path / "to_import.json"
        pm.export_presets(export_file)
        # Change local version
        pm.save_preset("imp", TraceOptions(filter_speckle=99))
        pm.import_presets(export_file, overwrite=False)
        assert pm.load_preset("imp").filter_speckle == 99

    def test_import_presets_with_overwrite(self, tmp_path: Path):
        pm.save_preset("imp", TraceOptions(filter_speckle=1))
        export_file = tmp_path / "to_import.json"
        pm.export_presets(export_file)
        pm.save_preset("imp", TraceOptions(filter_speckle=99))
        pm.import_presets(export_file, overwrite=True)
        assert pm.load_preset("imp").filter_speckle == 1

    def test_import_presets_from_bare_dict(self, tmp_path: Path):
        bare = {"bare_preset": {"colormode": "binary", "filter_speckle": 7}}
        file_path = tmp_path / "bare.json"
        file_path.write_text(json.dumps(bare), encoding="utf-8")
        pm.import_presets(file_path)
        loaded = pm.load_preset("bare_preset")
        assert loaded.colormode == "binary"
        assert loaded.filter_speckle == 7

    def test_import_presets_file_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            pm.import_presets(tmp_path / "missing.json")

    def test_import_presets_invalid_json(self, tmp_path: Path):
        bad = tmp_path / "bad.json"
        bad.write_text("[1, 2, 3]", encoding="utf-8")
        with pytest.raises(ValueError):
            pm.import_presets(bad)


class TestEdgeCases:
    def test_load_unknown_preset(self):
        with pytest.raises(ValueError, match="Unknown preset"):
            pm.load_preset("totally_unknown_preset_name")

    def test_corrupt_user_file_treated_as_empty(self, monkeypatch, tmp_path: Path):
        store = tmp_path / "presets.json"
        store.write_text("not json", encoding="utf-8")
        monkeypatch.setattr(pm, "_user_presets_file", lambda: store)
        assert pm.list_user_presets() == {}
        assert not pm.preset_exists("anything")

    def test_trace_options_from_dict_ignores_unknown_keys(self):
        raw = {"colormode": "binary", "future_field": 123}
        opts = pm._trace_options_from_dict(raw)
        assert opts.colormode == "binary"
        assert not hasattr(opts, "future_field")
