from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch


def make_fake_image(path: Path, size: tuple[int, int] = (100, 100), mode: str = "RGB") -> Path:
    """Create a minimal valid image file at *path*."""
    from PIL import Image

    img = Image.new(mode, size, color=(128, 128, 128))
    img.save(path)
    return path


def make_fake_svg(path: Path, content: str | None = None) -> Path:
    """Create a minimal SVG file at *path*."""
    if content is None:
        content = (
            '<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M0 0 L100 100" stroke="black"/>'
            "</svg>"
        )
    path.write_text(content, encoding="utf-8")
    return path


def mock_trace_image_pipeline(
    tmp_path: Path,
    *,
    engine: str = "python-vtracer",
    elapsed: float = 1.0,
    stats: dict[str, Any] | None = None,
    pdf_path: Path | None = None,
    png_path: Path | None = None,
    eps_path: Path | None = None,
):
    """Return a mock TraceResult and the patch target for trace_image."""
    from vector_studio.models import TraceResult

    if stats is None:
        stats = {"paths": 5}
    svg_path = tmp_path / "out.svg"
    svg_path.write_text("<svg></svg>")
    result = TraceResult(
        input_path=tmp_path / "in.png",
        svg_path=svg_path,
        engine=engine,
        elapsed_seconds=elapsed,
        stats=stats,
        pdf_path=pdf_path,
        png_path=png_path,
        eps_path=eps_path,
    )
    return result


def run_with_mock_tracer(monkeypatch, tmp_path: Path, fn, *args, **kwargs):
    """Run *fn* with trace_image fully mocked so no real VTracer is needed."""
    from vector_studio.models import TraceResult

    def _fake_trace(*a, **kw):
        out = kw.get("output_path", a[1] if len(a) > 1 else tmp_path / "out.svg")
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        if not out.exists():
            out.write_text("<svg></svg>")
        return TraceResult(
            input_path=Path(a[0]) if a else tmp_path / "in.png",
            svg_path=out,
            engine="mock",
            elapsed_seconds=0.1,
            stats={"paths": 3},
        )

    with patch("vector_studio.tracer.trace_image", side_effect=_fake_trace):
        return fn(*args, **kwargs)


def assert_svg_exists(path: Path) -> None:
    assert path.exists(), f"SVG not found: {path}"
    text = path.read_text(encoding="utf-8")
    assert "<svg" in text, f"File does not contain <svg tag: {path}"
