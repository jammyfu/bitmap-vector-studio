from pathlib import Path

from vector_studio.svg_tools import optimize_svg_file, optimize_svg_text, svg_stats


def test_optimize_svg_text_removes_comments_and_whitespace():
    raw = """
    <svg viewBox="0 0 10 10">
      <!-- remove me -->
      <path d="M0 0 L10 10" />
    </svg>
    """
    cleaned = optimize_svg_text(raw)
    assert "remove me" not in cleaned
    assert "> <" not in cleaned


def test_svg_stats(tmp_path: Path):
    svg = tmp_path / "sample.svg"
    svg.write_text('<svg viewBox="0 0 10 10"><path d="M0 0"/><path d="M1 1"/></svg>', encoding="utf-8")
    optimize_svg_file(svg)
    stats = svg_stats(svg)
    assert stats["paths"] == 2
    assert stats["viewBox"] == "0 0 10 10"
