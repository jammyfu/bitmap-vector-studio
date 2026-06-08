from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

_COMMENT_RE = re.compile(r"<!--.*?-->", flags=re.DOTALL)
_BETWEEN_TAGS_RE = re.compile(r">\s+<")
_MULTISPACE_RE = re.compile(r"\s{2,}")


def optimize_svg_text(svg_text: str) -> str:
    """A conservative SVG cleanup pass.

    VTracer already controls path precision, so this function avoids aggressive
    path-data rewriting and only removes comments / redundant whitespace.
    """
    cleaned = _COMMENT_RE.sub("", svg_text)
    cleaned = _BETWEEN_TAGS_RE.sub("><", cleaned)
    cleaned = "\n".join(line.strip() for line in cleaned.splitlines() if line.strip())
    cleaned = _MULTISPACE_RE.sub(" ", cleaned)
    return cleaned.strip() + "\n"


def optimize_svg_file(svg_path: Path) -> None:
    svg_path = Path(svg_path)
    text = svg_path.read_text(encoding="utf-8")
    svg_path.write_text(optimize_svg_text(text), encoding="utf-8")


def svg_stats(svg_path: Path) -> dict[str, Any]:
    svg_path = Path(svg_path)
    text = svg_path.read_text(encoding="utf-8", errors="replace")
    stats: dict[str, Any] = {
        "file_bytes": svg_path.stat().st_size,
        "paths": text.count("<path"),
        "polygons": text.count("<polygon"),
        "rects": text.count("<rect"),
        "circles": text.count("<circle"),
        "groups": text.count("<g"),
    }
    viewbox_match = re.search(r'viewBox="([^"]+)"', text)
    if viewbox_match:
        stats["viewBox"] = viewbox_match.group(1)
    return stats


def export_svg_to_pdf(svg_path: Path, output_path: Path) -> Path:
    try:
        import cairosvg
    except ImportError as exc:
        raise RuntimeError("PDF export requires cairosvg. Install with: pip install cairosvg") from exc

    svg_path = Path(svg_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2pdf(url=str(svg_path), write_to=str(output_path))
    return output_path


def export_svg_to_png(svg_path: Path, output_path: Path, scale: float = 1.0) -> Path:
    try:
        import cairosvg
    except ImportError as exc:
        raise RuntimeError("PNG export requires cairosvg. Install with: pip install cairosvg") from exc

    svg_path = Path(svg_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(url=str(svg_path), write_to=str(output_path), scale=scale)
    return output_path


def export_svg_to_eps_with_inkscape(svg_path: Path, output_path: Path) -> Path:
    """Export EPS using Inkscape CLI when available.

    Inkscape is not bundled with this template. Install it separately and ensure
    `inkscape` is available on PATH.
    """
    inkscape = shutil.which("inkscape")
    if not inkscape:
        raise RuntimeError("EPS export requires Inkscape CLI on PATH.")

    svg_path = Path(svg_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        inkscape,
        str(svg_path),
        "--export-type=eps",
        f"--export-filename={output_path}",
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "Inkscape EPS export failed.")
    return output_path
