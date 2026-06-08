from __future__ import annotations

import json
from pathlib import Path

import pytest

from vector_studio.community_tools import (
    ContributionGuideGenerator,
    PresetValidator,
    ReleaseNotesGenerator,
)


class TestPresetValidator:
    def test_valid_preset(self, tmp_path: Path):
        preset = tmp_path / "valid.json"
        preset.write_text(
            json.dumps(
                {
                    "name": "my_preset",
                    "options": {"colormode": "binary", "filter_speckle": 8},
                }
            ),
            encoding="utf-8",
        )
        passed, errors = PresetValidator.validate(preset)
        assert passed is True
        assert errors == []

    def test_missing_required_field(self, tmp_path: Path):
        preset = tmp_path / "bad.json"
        preset.write_text(json.dumps({"options": {}}), encoding="utf-8")
        passed, errors = PresetValidator.validate(preset)
        assert passed is False
        assert any("name" in e for e in errors)

    def test_invalid_trace_options(self, tmp_path: Path):
        preset = tmp_path / "invalid.json"
        preset.write_text(
            json.dumps(
                {
                    "name": "bad",
                    "options": {"colormode": "invalid_mode"},
                }
            ),
            encoding="utf-8",
        )
        passed, errors = PresetValidator.validate(preset)
        assert passed is False
        assert any("colormode" in e or "TraceOptions" in e for e in errors)

    def test_unknown_option_key(self, tmp_path: Path):
        preset = tmp_path / "unknown.json"
        preset.write_text(
            json.dumps(
                {
                    "name": "unknown",
                    "options": {"colormode": "color", "unknown_key": 123},
                }
            ),
            encoding="utf-8",
        )
        passed, errors = PresetValidator.validate(preset)
        assert passed is False
        assert any("unknown_key" in e for e in errors)

    def test_batch_validation(self, tmp_path: Path):
        good = tmp_path / "good.json"
        good.write_text(
            json.dumps({"name": "good", "options": {"colormode": "color"}}),
            encoding="utf-8",
        )
        bad = tmp_path / "bad.json"
        bad.write_text("not json", encoding="utf-8")
        results = PresetValidator.validate_batch(tmp_path)
        assert len(results) == 2
        by_name = {Path(r["path"]).name: r for r in results}
        assert by_name["good.json"]["passed"] is True
        assert by_name["bad.json"]["passed"] is False


class TestContributionGuideGenerator:
    def test_generate(self, tmp_path: Path):
        path = tmp_path / "CONTRIBUTING.md"
        ContributionGuideGenerator.generate(path)
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "Contributing to Bitmap Vector Studio" in content
        assert "Development Environment" in content
        assert "Pull Request Workflow" in content


class TestReleaseNotesGenerator:
    def test_generate_with_conventional_commits(self):
        commits = [
            {"message": "feat: add new filter plugin", "hash": "abc1234"},
            {"message": "fix: resolve SVG scaling issue", "hash": "def5678"},
            {"message": "docs: update README", "hash": "ghi9012"},
            {"message": "chore: bump dependencies", "hash": "jkl3456"},
        ]
        notes = ReleaseNotesGenerator.generate("1.2.0", commits)
        assert "Release 1.2.0" in notes
        assert "add new filter plugin" in notes
        assert "resolve SVG scaling issue" in notes
        assert "update README" in notes
        assert "bump dependencies" in notes

    def test_generate_with_unknown_commits(self):
        commits = [
            {"message": "random commit without convention"},
        ]
        notes = ReleaseNotesGenerator.generate("0.1.0", commits)
        assert "Release 0.1.0" in notes
        assert "random commit without convention" in notes
        assert "Other Changes" in notes
