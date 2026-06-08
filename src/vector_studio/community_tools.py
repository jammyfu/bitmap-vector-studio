from __future__ import annotations

import json
import re
from dataclasses import fields
from pathlib import Path
from typing import Any

from .models import TraceOptions


class PresetValidator:
    """Validate preset JSON files for correctness and TraceOptions compatibility."""

    REQUIRED_FIELDS: tuple[str, ...] = ("name", "options")

    @classmethod
    def validate(cls, preset_file: Path) -> tuple[bool, list[str]]:
        """Validate a single preset JSON file.

        Parameters
        ----------
        preset_file:
            Path to the ``.json`` preset file.

        Returns
        -------
        tuple[bool, list[str]]
            ``(passed, errors)`` where *errors* is a list of human-readable
            validation messages.
        """
        errors: list[str] = []
        path = Path(preset_file)

        if not path.exists():
            return False, [f"File not found: {path}"]

        if path.suffix != ".json":
            return False, [f"Not a JSON file: {path}"]

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return False, [f"Invalid JSON: {exc}"]
        except Exception as exc:
            return False, [f"Failed to read file: {exc}"]

        if not isinstance(raw, dict):
            return False, ["Preset must be a JSON object."]

        for field in cls.REQUIRED_FIELDS:
            if field not in raw:
                errors.append(f"Missing required field: '{field}'.")

        options = raw.get("options")
        if options is not None:
            if not isinstance(options, dict):
                errors.append("'options' must be an object.")
            else:
                # Validate against TraceOptions field names and ranges
                valid_fields = {f.name for f in fields(TraceOptions)}
                for key in options:
                    if key not in valid_fields:
                        errors.append(f"Unknown option key: '{key}'.")
                try:
                    TraceOptions(**options).validate()
                except (TypeError, ValueError) as exc:
                    errors.append(f"TraceOptions validation failed: {exc}")

        # Optional metadata checks
        if "version" in raw and not isinstance(raw["version"], str):
            errors.append("'version' must be a string.")

        passed = not errors
        return passed, errors

    @classmethod
    def validate_batch(cls, preset_dir: Path) -> list[dict[str, Any]]:
        """Validate every ``.json`` file in *preset_dir*.

        Returns
        -------
        list[dict]
            One dict per file with keys ``path``, ``passed``, ``errors``.
        """
        results: list[dict[str, Any]] = []
        directory = Path(preset_dir)
        if not directory.is_dir():
            return [{"path": str(directory), "passed": False, "errors": ["Not a directory."]}]
        for json_file in sorted(directory.glob("*.json")):
            passed, errors = cls.validate(json_file)
            results.append({"path": str(json_file), "passed": passed, "errors": errors})
        return results


class ContributionGuideGenerator:
    """Generate a CONTRIBUTING.md template for community contributors."""

    TEMPLATE: str = """\
# Contributing to Bitmap Vector Studio

Thank you for your interest in contributing! This document outlines the
workflow and standards we follow.

## Development Environment

1. Clone the repository.
2. Create a virtual environment: ``python -m venv .venv``
3. Install in editable mode: ``pip install -e '.[dev]'``
4. Run tests: ``pytest tests/``

## Code Style

- Follow PEP 8.
- Use type annotations for all public functions.
- Add docstrings in Google style.
- Keep functions focused and under 60 lines where possible.

## Testing Requirements

- All new features must include tests.
- Bug fixes should include a regression test.
- Aim for >80% coverage on new code.
- Run ``pytest tests/`` before submitting a PR.

## Pull Request Workflow

1. Fork the repository and create a feature branch.
2. Make your changes with clear, atomic commits.
3. Update documentation if needed.
4. Ensure the full test suite passes.
5. Open a PR with a descriptive title and summary.

## Plugin Contributions

- Place new plugins in ``src/vector_studio/builtin_plugins/`` or submit as
  standalone ``.py`` files.
- Use ``vector-studio plugin validate <file>`` to check your plugin.
- Include a README section for your plugin if it adds new options.

## Preset Contributions

- Validate presets with ``vector-studio validate preset <file>``.
- Presets must include ``name`` and ``options`` fields.

## Questions?

Open an issue or start a discussion. We are happy to help!
"""

    @classmethod
    def generate(cls, output_path: Path) -> Path:
        """Write the CONTRIBUTING.md template to *output_path*.

        Returns
        -------
        Path
            The written file path.
        """
        path = Path(output_path)
        path.write_text(cls.TEMPLATE, encoding="utf-8")
        return path


class ReleaseNotesGenerator:
    """Generate release notes from commit history using Conventional Commits."""

    TYPE_EMOJI: dict[str, str] = {
        "feat": "✨ Features",
        "fix": "🐛 Bug Fixes",
        "docs": "📚 Documentation",
        "style": "💎 Styles",
        "refactor": "♻️ Code Refactoring",
        "perf": "⚡ Performance",
        "test": "✅ Tests",
        "chore": "🔧 Chores",
        "ci": "👷 CI/CD",
        "build": "📦 Build",
        "revert": "⏪ Reverts",
    }

    @classmethod
    def generate(cls, version: str, commits: list[dict[str, Any]]) -> str:
        """Generate a Markdown release notes string.

        Parameters
        ----------
        version:
            Release version, e.g. ``"1.2.0"``.
        commits:
            List of commit dicts with keys ``message`` (str) and
            optionally ``hash`` (str), ``author`` (str), ``date`` (str).

        Returns
        -------
        str
            Markdown release notes.
        """
        lines = [f"# Release {version}", ""]

        grouped: dict[str, list[str]] = {}
        unknown: list[str] = []

        for commit in commits:
            msg = commit.get("message", "")
            match = re.match(r"^(\w+)(\(.+\))?!?:\s*(.+)$", msg)
            if match:
                ctype = match.group(1)
                body = match.group(3)
                header = cls.TYPE_EMOJI.get(ctype, f"📌 {ctype.capitalize()}")
                entry = f"- {body}"
                if "hash" in commit:
                    entry += f" (`{commit['hash'][:7]}`)"
                grouped.setdefault(header, []).append(entry)
            else:
                entry = f"- {msg}"
                if "hash" in commit:
                    entry += f" (`{commit['hash'][:7]}`)"
                unknown.append(entry)

        for header in sorted(grouped.keys(), key=lambda h: list(cls.TYPE_EMOJI.values()).index(h) if h in cls.TYPE_EMOJI.values() else 999):
            lines.append(f"## {header}")
            lines.append("")
            for entry in grouped[header]:
                lines.append(entry)
            lines.append("")

        if unknown:
            lines.append("## 📌 Other Changes")
            lines.append("")
            for entry in unknown:
                lines.append(entry)
            lines.append("")

        return "\n".join(lines)
