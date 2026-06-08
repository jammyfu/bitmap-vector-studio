from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
SRC = ROOT / "src"
TESTS = ROOT / "tests"

EXCLUDE_PATTERNS = [
    ".venv",
    "venv",
    "node_modules",
    ".git",
    "__pycache__",
    ".pytest_cache",
    "*.egg-info",
    "build",
    "dist",
    ".github",
    ".idea",
    ".vscode",
    "*.pyc",
    "*.pyo",
    ".DS_Store",
    "Thumbs.db",
]


def _print(msg: str) -> None:
    print(f"[package] {msg}")


def clean() -> None:
    """Remove build artifacts and caches."""
    _print("Cleaning build artifacts...")
    patterns = [
        ROOT / "build",
        ROOT / "dist",
        ROOT / "*.egg-info",
    ]
    removed = 0
    for pattern in patterns:
        for path in ROOT.glob(pattern.name if pattern.name != "*.egg-info" else "*.egg-info"):
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
                _print(f"  removed {path.relative_to(ROOT)}")
                removed += 1

    # Recursively remove __pycache__ and .pytest_cache
    for cache_name in ("__pycache__", ".pytest_cache"):
        for cache_dir in ROOT.rglob(cache_name):
            if cache_dir.is_dir():
                shutil.rmtree(cache_dir, ignore_errors=True)
                _print(f"  removed {cache_dir.relative_to(ROOT)}")
                removed += 1

    if removed == 0:
        _print("  nothing to clean")
    else:
        _print(f"  total removed: {removed}")


def run_lint() -> bool:
    """Run ruff check; return True on success."""
    _print("Running lint (ruff check src/ tests/)...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", str(SRC), str(TESTS)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        _print("  ERROR: ruff is not installed. Run: pip install ruff")
        return False

    if result.returncode != 0:
        _print("  LINT FAILED:")
        print(result.stdout or result.stderr)
        return False

    _print("  lint passed")
    return True


def run_tests() -> bool:
    """Run pytest; return True on success."""
    _print("Running tests (pytest tests/ -v)...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(TESTS), "-v"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        _print("  ERROR: pytest is not installed. Run: pip install pytest")
        return False

    if result.returncode != 0:
        _print("  TESTS FAILED:")
        print(result.stdout or result.stderr)
        return False

    _print("  tests passed")
    return True


def build_wheel() -> bool:
    """Build wheel and sdist with python -m build."""
    _print("Building wheel and sdist (python -m build)...")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "build"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        _print("  ERROR: build is not installed. Run: pip install build")
        return False

    if result.returncode != 0:
        _print("  BUILD FAILED:")
        print(result.stdout or result.stderr)
        return False

    _print("  build succeeded")
    # List what was produced
    for item in sorted(DIST.iterdir()) if DIST.exists() else []:
        _print(f"    -> {item.name}")
    return True


def _should_exclude(rel_path: Path) -> bool:
    """Check whether a relative path matches any exclusion pattern."""
    parts = rel_path.parts
    for part in parts:
        for pat in EXCLUDE_PATTERNS:
            if pat.startswith("*"):
                if part.endswith(pat[1:]) or part == pat[1:]:
                    return True
            else:
                if part == pat:
                    return True
    return False


def create_zip() -> bool:
    """Create a source ZIP archive, excluding unnecessary files."""
    DIST.mkdir(parents=True, exist_ok=True)
    zip_path = DIST / "bitmap-vector-studio-0.2.0-src.zip"
    _print(f"Creating source ZIP: {zip_path.name}...")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in ROOT.rglob("*"):
            if path.is_file():
                rel = path.relative_to(ROOT)
                if _should_exclude(rel):
                    continue
                zf.write(path, rel)

    size = zip_path.stat().st_size
    _print(f"  created {zip_path.name} ({size:,} bytes)")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Package script for Bitmap Vector Studio",
    )
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest")
    parser.add_argument("--skip-lint", action="store_true", help="Skip ruff check")
    parser.add_argument("--only-wheel", action="store_true", help="Only build wheel")
    parser.add_argument("--only-zip", action="store_true", help="Only create source ZIP")
    args = parser.parse_args()

    if args.only_wheel and args.only_zip:
        _print("ERROR: --only-wheel and --only-zip are mutually exclusive")
        return 1

    if args.only_wheel:
        clean()
        if not args.skip_lint and not run_lint():
            return 1
        if not args.skip_tests and not run_tests():
            return 1
        if not build_wheel():
            return 1
        return 0

    if args.only_zip:
        clean()
        if not create_zip():
            return 1
        return 0

    # Full pipeline
    clean()
    if not args.skip_lint and not run_lint():
        return 1
    if not args.skip_tests and not run_tests():
        return 1
    if not build_wheel():
        return 1
    if not create_zip():
        return 1

    _print("All packaging steps completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
