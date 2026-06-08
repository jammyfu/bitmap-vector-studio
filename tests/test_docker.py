"""Simple validation tests for Docker packaging."""

from __future__ import annotations

import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_dockerfile_exists() -> None:
    """Ensure Dockerfile is present."""
    dockerfile = PROJECT_ROOT / "Dockerfile"
    assert dockerfile.exists(), "Dockerfile not found"


def test_dockerfile_has_required_stages() -> None:
    """Ensure Dockerfile contains expected multi-stage targets."""
    dockerfile = PROJECT_ROOT / "Dockerfile"
    content = dockerfile.read_text(encoding="utf-8")
    assert "AS builder" in content, "Missing builder stage"
    assert "AS runtime" in content, "Missing runtime stage"
    assert "AS cli" in content, "Missing cli stage"
    assert "EXPOSE 8000" in content, "Missing port exposure"
    assert "HEALTHCHECK" in content, "Missing health check"


def test_docker_compose_exists() -> None:
    """Ensure docker-compose.yml is present."""
    compose = PROJECT_ROOT / "docker-compose.yml"
    assert compose.exists(), "docker-compose.yml not found"


def test_dockerignore_exists() -> None:
    """Ensure .dockerignore is present."""
    ignore = PROJECT_ROOT / ".dockerignore"
    assert ignore.exists(), ".dockerignore not found"


def test_dockerignore_excludes() -> None:
    """Ensure .dockerignore excludes common artifacts."""
    ignore = PROJECT_ROOT / ".dockerignore"
    content = ignore.read_text(encoding="utf-8")
    for pattern in (".git", "__pycache__", ".venv", "dist", "build", ".pytest_cache"):
        assert pattern in content, f".dockerignore should exclude {pattern}"


def test_release_script_exists() -> None:
    """Ensure release.py is present and executable."""
    release = PROJECT_ROOT / "scripts" / "release.py"
    assert release.exists(), "scripts/release.py not found"


def test_install_script_exists() -> None:
    """Ensure install.sh is present."""
    install = PROJECT_ROOT / "scripts" / "install.sh"
    assert install.exists(), "scripts/install.sh not found"


def test_github_release_workflow_exists() -> None:
    """Ensure release workflow is present."""
    workflow = PROJECT_ROOT / ".github" / "workflows" / "release.yml"
    assert workflow.exists(), ".github/workflows/release.yml not found"


def test_packaging_templates_exist() -> None:
    """Ensure packaging templates are present."""
    homebrew = PROJECT_ROOT / "packaging" / "homebrew" / "bitmap-vector-studio.rb"
    nuspec = PROJECT_ROOT / "packaging" / "chocolatey" / "bitmap-vector-studio.nuspec"
    choco_install = PROJECT_ROOT / "packaging" / "chocolatey" / "tools" / "chocolateyinstall.ps1"
    deb = PROJECT_ROOT / "packaging" / "apt" / "build-deb.sh"
    for path in (homebrew, nuspec, choco_install, deb):
        assert path.exists(), f"Packaging template missing: {path}"
