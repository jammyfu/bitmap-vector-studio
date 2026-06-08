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



def make_fake_prepare_input_side_effect(normalized_path: Path | None = None):
    """Return a side_effect callable for mocking tracer.prepare_input.

    The callable creates a minimal valid PNG at *normalized_input* so that
    downstream PIL.open() calls do not raise FileNotFoundError.
    """
    from PIL import Image

    def _side_effect(input_path, normalized_input, options, **kwargs):
        target = normalized_path or normalized_input
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (10, 10)).save(target)
        return target

    return _side_effect


def patch_trace_image_for_test(
    tmp_path: Path,
    *,
    engine: str = "python-vtracer",
    create_svg: bool = True,
    create_pdf: bool = False,
    create_png: bool = False,
    create_eps: bool = False,
):
    """Return a context-manager stack that fully mocks trace_image internals.

    Usage inside a *with* statement:

        with patch_trace_image_for_test(tmp_path) as mocks:
            result = trace_image(img, out)
    """
    from contextlib import ExitStack
    from vector_studio.models import TraceResult

    stack = ExitStack()

    def _fake_prepare(input_path, normalized_input, options, **kwargs):
        from PIL import Image
        normalized_input = Path(normalized_input)
        normalized_input.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (10, 10)).save(normalized_input)
        return normalized_input

    stack.enter_context(patch("vector_studio.tracer.prepare_input", side_effect=_fake_prepare))
    stack.enter_context(patch("vector_studio.tracer._trace_with_python_binding"))
    stack.enter_context(patch("vector_studio.tracer.optimize_svg_file"))
    stack.enter_context(patch("vector_studio.tracer.svg_stats", return_value={"paths": 3}))

    if create_pdf:
        pdf = tmp_path / "out.pdf"
        pdf.write_bytes(b"pdf")
        stack.enter_context(patch("vector_studio.tracer.export_svg_to_pdf", return_value=pdf))
    if create_png:
        png = tmp_path / "out.png"
        png.write_bytes(b"png")
        stack.enter_context(patch("vector_studio.tracer.export_svg_to_png", return_value=png))
    if create_eps:
        eps = tmp_path / "out.eps"
        eps.write_bytes(b"eps")
        stack.enter_context(patch("vector_studio.tracer.export_svg_to_eps_with_inkscape", return_value=eps))

    return stack


def assert_trace_result_valid(result: "TraceResult", *, expect_svg: bool = True) -> None:
    """Assert that a TraceResult has sensible values."""
    assert result.elapsed_seconds >= 0
    assert result.input_path.exists()
    if expect_svg:
        assert result.svg_path.exists()
        assert result.svg_path.suffix == ".svg"
    assert result.engine
    assert isinstance(result.stats, dict)
