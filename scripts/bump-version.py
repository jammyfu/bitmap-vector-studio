#!/usr/bin/env python3
"""同步所有模块的版本号."""

import re
import sys
from pathlib import Path


def bump_version(new_version: str):
    root = Path(__file__).parent.parent

    # Python pyproject.toml
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text(encoding="utf-8")
        content = re.sub(
            r'^version = "[^"]+"',
            f'version = "{new_version}"',
            content,
            flags=re.M,
        )
        pyproject.write_text(content, encoding="utf-8")
        print(f"  [OK] pyproject.toml -> {new_version}")
    else:
        print(f"  [SKIP] pyproject.toml not found")

    # Python __init__.py
    init = root / "src" / "vector_studio" / "__init__.py"
    if init.exists():
        content = init.read_text(encoding="utf-8")
        content = re.sub(
            r'__version__ = "[^"]+"',
            f'__version__ = "{new_version}"',
            content,
        )
        init.write_text(content, encoding="utf-8")
        print(f"  [OK] src/vector_studio/__init__.py -> {new_version}")
    else:
        print(f"  [SKIP] src/vector_studio/__init__.py not found")

    # Rust Cargo.toml
    cargo = root / "desktop" / "src-tauri" / "Cargo.toml"
    if cargo.exists():
        content = cargo.read_text(encoding="utf-8")
        content = re.sub(
            r'^version = "[^"]+"',
            f'version = "{new_version}"',
            content,
            flags=re.M,
        )
        cargo.write_text(content, encoding="utf-8")
        print(f"  [OK] desktop/src-tauri/Cargo.toml -> {new_version}")
    else:
        print(f"  [SKIP] desktop/src-tauri/Cargo.toml not found")

    # Node package.json
    pkg = root / "desktop" / "package.json"
    if pkg.exists():
        content = pkg.read_text(encoding="utf-8")
        content = re.sub(
            r'"version": "[^"]+"',
            f'"version": "{new_version}"',
            content,
        )
        pkg.write_text(content, encoding="utf-8")
        print(f"  [OK] desktop/package.json -> {new_version}")
    else:
        print(f"  [SKIP] desktop/package.json not found")

    # Tauri conf
    conf = root / "desktop" / "src-tauri" / "tauri.conf.json"
    if conf.exists():
        content = conf.read_text(encoding="utf-8")
        content = re.sub(
            r'"version": "[^"]+"',
            f'"version": "{new_version}"',
            content,
        )
        conf.write_text(content, encoding="utf-8")
        print(f"  [OK] desktop/src-tauri/tauri.conf.json -> {new_version}")
    else:
        print(f"  [SKIP] desktop/src-tauri/tauri.conf.json not found")

    print(f"\nVersion bumped to {new_version}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python bump-version.py <version>")
        print("Example: python bump-version.py 3.1.0")
        sys.exit(1)
    bump_version(sys.argv[1])
