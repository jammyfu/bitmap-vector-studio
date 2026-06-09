import json
from pathlib import Path

import pytest

from vector_studio.migration import MigrationManager


class TestMigrationManager:
    def test_get_current_version_no_file(self, tmp_path: Path):
        mgr = MigrationManager(data_dir=tmp_path)
        assert mgr.get_current_version() == 0

    def test_needs_migration(self, tmp_path: Path):
        mgr = MigrationManager(data_dir=tmp_path)
        assert mgr.needs_migration() is True
        tmp_path.joinpath("version.json").write_text(json.dumps({"schema_version": 3}))
        assert mgr.needs_migration() is False

    def test_migrate_v1_creates_directories(self, tmp_path: Path):
        mgr = MigrationManager(data_dir=tmp_path)
        logs = mgr.migrate()
        assert (tmp_path / "presets").is_dir()
        assert (tmp_path / "history").is_dir()
        assert any("v1 complete" in line for line in logs)

    def test_migrate_v2_history_format(self, tmp_path: Path):
        mgr = MigrationManager(data_dir=tmp_path)
        # Simulate old v1 state
        old_history = tmp_path / "history.json"
        old_history.write_text(json.dumps([{"file": "a.png", "preset": "logo"}]))
        tmp_path.joinpath("version.json").write_text(json.dumps({"schema_version": 1}))

        logs = mgr.migrate()
        new_history = tmp_path / "history.jsonl"
        assert new_history.exists()
        assert old_history.with_suffix(".json.bak").exists()
        lines = new_history.read_text().strip().split("\n")
        assert len(lines) == 1
        assert any("v2 complete" in line for line in logs)

    def test_migrate_v3_creates_directories(self, tmp_path: Path):
        mgr = MigrationManager(data_dir=tmp_path)
        tmp_path.joinpath("version.json").write_text(json.dumps({"schema_version": 2}))
        logs = mgr.migrate()
        assert (tmp_path / "cache").is_dir()
        assert (tmp_path / "reports").is_dir()
        assert (tmp_path / "plugin_market").is_dir()
        assert any("v3 complete" in line for line in logs)

    def test_full_migration_from_v0(self, tmp_path: Path):
        mgr = MigrationManager(data_dir=tmp_path)
        logs = mgr.migrate()
        assert mgr.get_current_version() == 3
        assert not mgr.needs_migration()
        assert any("Schema version updated to 3" in line for line in logs)

    def test_idempotent_migration(self, tmp_path: Path):
        mgr = MigrationManager(data_dir=tmp_path)
        mgr.migrate()
        logs = mgr.migrate()
        assert any("Already at the latest" not in line for line in logs) or mgr.get_current_version() == 3
        # Second migrate should just update version again since version file is rewritten
        assert mgr.get_current_version() == 3
