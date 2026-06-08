#!/usr/bin/env python3
"""Automated release script for Bitmap Vector Studio.

Usage:
    python scripts/release.py --part patch --dry-run
    python scripts/release.py --part minor --skip-tests
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = PROJECT_ROOT / "pyproject.toml"
INIT_PY = PROJECT_ROOT / "src" / "vector_studio" / "__init__.py"
API_PY = PROJECT_ROOT / "src" / "vector_studio" / "api.py"


def _run(cmd: list[str], check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command with clear error handling."""
    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            check=check,
            capture_output=capture,
            text=True,
        )
        return result
    except subprocess.CalledProcessError as exc:
        print(f"[ERROR] Command failed: {' '.join(cmd)}")
        if exc.stdout:
            print(exc.stdout)
        if exc.stderr:
            print(exc.stderr, file=sys.stderr)
        raise


def _current_version() -> str:
    """Read current version from pyproject.toml."""
    text = PYPROJECT.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise RuntimeError("Could not find version in pyproject.toml")
    return match.group(1)


def _bump_version(part: str) -> str:
    """Bump version in pyproject.toml, __init__.py and api.py."""
    current = _current_version()
    major, minor, patch = map(int, current.split("."))

    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    elif part == "patch":
        patch += 1
    else:
        raise ValueError(f"Invalid bump part: {part}")

    new_version = f"{major}.{minor}.{patch}"

    # Update pyproject.toml
    content = PYPROJECT.read_text(encoding="utf-8")
    content = re.sub(
        r'^(version\s*=\s*")([^"]+)(")',
        lambda m: f'{m.group(1)}{new_version}{m.group(3)}',
        content,
        flags=re.MULTILINE,
    )
    PYPROJECT.write_text(content, encoding="utf-8")

    # Update __init__.py
    init_content = INIT_PY.read_text(encoding="utf-8")
    init_content = re.sub(
        r'^(__version__\s*=\s*")([^"]+)(")',
        lambda m: f'{m.group(1)}{new_version}{m.group(3)}',
        init_content,
        flags=re.MULTILINE,
    )
    INIT_PY.write_text(init_content, encoding="utf-8")

    # Update api.py
    api_content = API_PY.read_text(encoding="utf-8")
    api_content = re.sub(
        r'^(\s*version\s*=\s*")([^"]+)(")',
        lambda m: f'{m.group(1)}{new_version}{m.group(3)}',
        api_content,
        flags=re.MULTILINE,
    )
    API_PY.write_text(api_content, encoding="utf-8")

    print(f"[OK] Bumped version: {current} -> {new_version}")
    return new_version


def _git_commit_version(new_version: str) -> None:
    """Commit version bump."""
    _run(["git", "add", "pyproject.toml", "src/vector_studio/__init__.py", "src/vector_studio/api.py"])
    _run(["git", "commit", "-m", f"chore(release): bump version to {new_version}"])
    print(f"[OK] Committed version bump")


def build() -> None:
    """Build wheel and sdist."""
    print("[INFO] Building wheel and sdist...")
    _run([sys.executable, "-m", "pip", "install", "--upgrade", "build"])
    _run([sys.executable, "-m", "build"])
    print("[OK] Build complete")


def test() -> None:
    """Run the full test suite."""
    print("[INFO] Running tests...")
    _run([sys.executable, "-m", "pytest", "tests/", "-v"])
    print("[OK] Tests passed")


def tag(version: str) -> None:
    """Create and push git tag."""
    tag_name = f"v{version}"
    print(f"[INFO] Creating git tag {tag_name}...")
    _run(["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}"])
    print(f"[OK] Tag {tag_name} created")


def push(version: str) -> None:
    """Push commits and tags to GitHub."""
    print("[INFO] Pushing to origin...")
    _run(["git", "push"])
    _run(["git", "push", "origin", f"v{version}"])
    print("[OK] Push complete")


def main() -> int:
    parser = argparse.ArgumentParser(description="Release script for Bitmap Vector Studio")
    parser.add_argument("--part", choices=["patch", "minor", "major"], default="patch", help="Version bump part")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without executing")
    parser.add_argument("--skip-tests", action="store_true", help="Skip running tests")
    args = parser.parse_args()

    dry_run = args.dry_run
    skip_tests = args.skip_tests

    current = _current_version()
    print(f"[INFO] Current version: {current}")

    # 1. Test
    if not skip_tests:
        if dry_run:
            print("[DRY-RUN] Would run tests")
        else:
            test()
    else:
        print("[INFO] Skipping tests")

    # 2. Bump version
    if dry_run:
        major, minor, patch = map(int, current.split("."))
        if args.part == "major":
            major += 1; minor = 0; patch = 0
        elif args.part == "minor":
            minor += 1; patch = 0
        else:
            patch += 1
        new_version = f"{major}.{minor}.{patch}"
        print(f"[DRY-RUN] Would bump version to {new_version}")
    else:
        new_version = _bump_version(args.part)
        _git_commit_version(new_version)

    # 3. Build
    if dry_run:
        print("[DRY-RUN] Would build wheel and sdist")
    else:
        build()

    # 4. Tag
    if dry_run:
        print(f"[DRY-RUN] Would create tag v{new_version}")
    else:
        tag(new_version)

    # 5. Push
    if dry_run:
        print(f"[DRY-RUN] Would push commits and tag v{new_version}")
    else:
        push(new_version)

    print(f"\n[SUCCESS] Release {new_version} complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
