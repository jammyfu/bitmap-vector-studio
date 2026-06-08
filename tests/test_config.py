from __future__ import annotations

from pathlib import Path

import pytest

from vector_studio.config import Config


class TestConfigDefaults:
    def test_default_values(self):
        cfg = Config()
        assert cfg.default_preset == "poster"
        assert cfg.default_output_dir is None
        assert cfg.default_optimize_level == "basic"
        assert cfg.smart_remove_bg is False
        assert cfg.enhance is None
        assert cfg.export_pdf is False
        assert cfg.export_png is False
        assert cfg.editor_preference is None
        assert cfg.max_workers == 4
        assert cfg.plugin_dirs == []
        assert cfg.enabled_plugins == []


class TestConfigSerialization:
    def test_to_dict_roundtrip(self):
        cfg = Config(
            default_preset="logo",
            default_output_dir=Path("/tmp/out"),
            max_workers=8,
            enabled_plugins=["watermark"],
        )
        data = cfg.to_dict()
        restored = Config.from_dict(data)
        assert restored.default_preset == "logo"
        assert restored.default_output_dir == Path("/tmp/out")
        assert restored.max_workers == 8
        assert restored.enabled_plugins == ["watermark"]

    def test_from_dict_ignores_unknown_keys(self):
        data = {"default_preset": "photo", "unknown_key": "ignored"}
        cfg = Config.from_dict(data)
        assert cfg.default_preset == "photo"
        assert not hasattr(cfg, "unknown_key")

    def test_save_and_load_json(self, tmp_path):
        cfg = Config(default_preset="bw", max_workers=2)
        path = tmp_path / "config.json"
        cfg.save(path)
        loaded = Config.load(path)
        assert loaded.default_preset == "bw"
        assert loaded.max_workers == 2

    def test_load_nonexistent_returns_defaults(self, tmp_path):
        missing = tmp_path / "missing.json"
        cfg = Config.load(missing)
        assert cfg.default_preset == "poster"

    def test_load_malformed_returns_defaults(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("not json")
        cfg = Config.load(bad)
        assert cfg.default_preset == "poster"


class TestConfigMerge:
    def test_merge_with_options_override(self):
        cfg = Config(default_preset="poster", export_pdf=False)
        merged = cfg.merge_with_options(preset="logo", export_pdf=True)
        assert merged["preset"] == "logo"
        assert merged["export_pdf"] is True

    def test_merge_with_options_none_ignored(self):
        cfg = Config(default_preset="poster")
        merged = cfg.merge_with_options(preset=None)
        assert merged["preset"] == "poster"

    def test_merge_includes_config_defaults(self):
        cfg = Config(default_optimize_level="comprehensive", smart_remove_bg=True)
        merged = cfg.merge_with_options()
        assert merged["optimize_level"] == "comprehensive"
        assert merged["smart_remove_bg"] is True


class TestConfigValidation:
    def test_valid_config(self):
        cfg = Config()
        assert cfg.validate() == []

    def test_invalid_optimize_level(self):
        cfg = Config(default_optimize_level="super")
        errors = cfg.validate()
        assert any("optimize_level" in e for e in errors)

    def test_invalid_max_workers(self):
        cfg = Config(max_workers=0)
        errors = cfg.validate()
        assert any("max_workers" in e for e in errors)

    def test_invalid_output_dir_type(self):
        cfg = Config()
        # Manually set to a bad type to test validation
        object.__setattr__(cfg, "default_output_dir", "not_a_path")
        errors = cfg.validate()
        assert any("default_output_dir" in e for e in errors)


class TestConfigInit:
    def test_init_creates_file(self, tmp_path):
        path = tmp_path / "config.json"
        cfg = Config()
        cfg.save(path)
        assert path.exists()
        loaded = Config.load(path)
        assert loaded.default_preset == "poster"
