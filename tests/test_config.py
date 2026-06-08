from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

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


class TestConfigMergeExtended:
    def test_merge_preserves_bool_false(self):
        cfg = Config(smart_remove_bg=True)
        merged = cfg.merge_with_options(smart_remove_bg=False)
        assert merged["smart_remove_bg"] is False

    def test_merge_preserves_explicit_zero(self):
        cfg = Config(max_workers=4)
        merged = cfg.merge_with_options(max_workers=0)
        assert merged["max_workers"] == 0

    def test_merge_ignores_none_for_existing(self):
        cfg = Config(default_preset="logo")
        merged = cfg.merge_with_options(default_preset=None)
        assert merged["preset"] == "logo"

    def test_merge_includes_all_mapped_keys(self):
        cfg = Config(
            default_preset="photo",
            default_optimize_level="comprehensive",
            smart_remove_bg=True,
            enhance="scan",
            export_pdf=True,
            export_png=True,
            editor_preference="inkscape",
            max_workers=8,
        )
        merged = cfg.merge_with_options()
        assert merged["preset"] == "photo"
        assert merged["optimize_level"] == "comprehensive"
        assert merged["smart_remove_bg"] is True
        assert merged["enhance"] == "scan"
        assert merged["export_pdf"] is True
        assert merged["export_png"] is True
        assert merged["editor"] == "inkscape"
        assert merged["workers"] == 8


class TestConfigYaml:
    def test_save_and_load_yaml(self, tmp_path):
        pytest.importorskip("yaml")
        from vector_studio.config import Config
        cfg = Config(default_preset="bw", max_workers=2)
        path = tmp_path / "config.yaml"
        cfg.save(path)
        assert path.exists()
        loaded = Config.load(path)
        assert loaded.default_preset == "bw"
        assert loaded.max_workers == 2

    def test_load_yaml_preferred_over_json(self, tmp_path):
        pytest.importorskip("yaml")
        from vector_studio.config import Config
        json_cfg = Config(default_preset="photo")
        yaml_cfg = Config(default_preset="logo")
        json_path = tmp_path / "config.json"
        yaml_path = tmp_path / "config.yaml"
        json_cfg.save(json_path)
        yaml_cfg.save(yaml_path)
        # When both exist, yaml is preferred
        with patch("vector_studio.config._default_config_path", return_value=yaml_path):
            loaded = Config.load()
        assert loaded.default_preset == "logo"


class TestConfigValidationExtended:
    def test_validate_negative_max_workers(self):
        cfg = Config(max_workers=-1)
        errors = cfg.validate()
        assert any("max_workers" in e for e in errors)

    def test_validate_optimize_level_edge_cases(self):
        for level in ["none", "basic", "comprehensive", "aggressive"]:
            cfg = Config(default_optimize_level=level)
            assert cfg.validate() == []

    def test_validate_empty_string_optimize_level(self):
        cfg = Config(default_optimize_level="")
        errors = cfg.validate()
        assert any("optimize_level" in e for e in errors)

    def test_validate_path_none_ok(self):
        cfg = Config(default_output_dir=None)
        assert cfg.validate() == []

    def test_from_dict_with_path_string(self):
        data = {"default_output_dir": "/tmp/out"}
        cfg = Config.from_dict(data)
        assert cfg.default_output_dir == Path("/tmp/out")

    def test_from_dict_with_none_path(self):
        data = {"default_output_dir": None}
        cfg = Config.from_dict(data)
        assert cfg.default_output_dir is None
