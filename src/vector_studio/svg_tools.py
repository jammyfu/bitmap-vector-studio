from __future__ import annotations

import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

_COMMENT_RE = re.compile(r"<!--.*?-->", flags=re.DOTALL)
_BETWEEN_TAGS_RE = re.compile(r">\s+<")
_MULTISPACE_RE = re.compile(r"\s{2,}")

# Common SVG namespaces
_SVG_NS = "http://www.w3.org/2000/svg"
_INKSCAPE_NS = "http://www.inkscape.org/namespaces/inkscape"
_SODIPODI_NS = "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"

# Register namespaces so ElementTree writes them with proper prefixes.
ET.register_namespace("", _SVG_NS)
ET.register_namespace("inkscape", _INKSCAPE_NS)
ET.register_namespace("sodipodi", _SODIPODI_NS)

# Regex helpers for color extraction
_COLOR_HEX_RE = re.compile(r"#([0-9a-fA-F]{3,8})\b")
_COLOR_RGB_RE = re.compile(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)")
_COLOR_KEYWORDS = {
    "black", "white", "red", "green", "blue", "yellow", "cyan", "magenta",
    "orange", "purple", "pink", "brown", "gray", "grey", "lime", "navy",
    "teal", "silver", "gold", "indigo", "violet", "turquoise", "coral",
}


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


def _get_local_name(tag: str) -> str:
    """Strip namespace prefix from an ElementTree tag."""
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def _parse_color(value: str | None) -> str | None:
    """Normalize a raw color string to #rrggbb or a keyword, or None."""
    if not value:
        return None
    value = value.strip().lower()
    if value in ("none", "currentcolor", "transparent", "inherit"):
        return None
    if value in _COLOR_KEYWORDS:
        return value
    hex_match = _COLOR_HEX_RE.match(value)
    if hex_match:
        hex_val = hex_match.group(1)
        if len(hex_val) == 3:
            hex_val = "".join(c * 2 for c in hex_val)
        elif len(hex_val) == 4:
            hex_val = "".join(c * 2 for c in hex_val[:3])
        elif len(hex_val) == 8:
            hex_val = hex_val[:6]
        return f"#{hex_val.lower()}"
    rgb_match = _COLOR_RGB_RE.match(value)
    if rgb_match:
        r, g, b = int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3))
        return f"#{r:02x}{g:02x}{b:02x}"
    return None


def _extract_colors_from_element(elem: ET.Element) -> dict[str, str | None]:
    """Extract fill and stroke colors from an element, including inline styles."""
    fill: str | None = None
    stroke: str | None = None
    style = elem.get("style", "")
    if style:
        for part in style.split(";"):
            if ":" in part:
                key, val = part.split(":", 1)
                key = key.strip().lower()
                if key == "fill":
                    fill = _parse_color(val)
                elif key == "stroke":
                    stroke = _parse_color(val)
    raw_fill = elem.get("fill")
    raw_stroke = elem.get("stroke")
    if raw_fill is not None:
        fill = _parse_color(raw_fill)
    if raw_stroke is not None:
        stroke = _parse_color(raw_stroke)
    return {"fill": fill, "stroke": stroke}


def _extract_all_colors(text: str) -> dict[str, int]:
    """Scan raw SVG text for every color occurrence."""
    counts: dict[str, int] = {}
    # Hex colors
    for m in _COLOR_HEX_RE.finditer(text):
        hex_val = m.group(1)
        if len(hex_val) == 3:
            hex_val = "".join(c * 2 for c in hex_val)
        elif len(hex_val) == 4:
            hex_val = "".join(c * 2 for c in hex_val[:3])
        elif len(hex_val) == 8:
            hex_val = hex_val[:6]
        color = f"#{hex_val.lower()}"
        counts[color] = counts.get(color, 0) + 1
    # rgb()
    for m in _COLOR_RGB_RE.finditer(text):
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        color = f"#{r:02x}{g:02x}{b:02x}"
        counts[color] = counts.get(color, 0) + 1
    # Keywords in attribute values
    for kw in _COLOR_KEYWORDS:
        pattern = re.compile(rf'[="\']\s*{re.escape(kw)}\s*["\']', re.IGNORECASE)
        counts[kw] = counts.get(kw, 0) + len(pattern.findall(text))
    return counts


def _bbox_from_path_d(d: str | None) -> list[float] | None:
    """Compute a rough bounding box from path data by scanning all numbers."""
    if not d:
        return None
    nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", d)]
    if len(nums) < 2:
        return None
    xs = nums[0::2]
    ys = nums[1::2]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    return [min_x, min_y, max_x - min_x, max_y - min_y]


def _bbox_from_rect(elem: ET.Element) -> list[float] | None:
    try:
        x = float(elem.get("x", "0"))
        y = float(elem.get("y", "0"))
        w = float(elem.get("width", "0"))
        h = float(elem.get("height", "0"))
        return [x, y, w, h]
    except ValueError:
        return None


def _bbox_from_polygon(points: str | None) -> list[float] | None:
    if not points:
        return None
    nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", points)]
    if len(nums) < 2:
        return None
    xs = nums[0::2]
    ys = nums[1::2]
    return [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)]


def _make_layer_name(index: int, colors: dict[str, str | None], strategy: str) -> str:
    """Generate a human-readable layer name."""
    fill = colors.get("fill")
    stroke = colors.get("stroke")
    if strategy == "color":
        if fill:
            return f"layer_{fill.replace('#', '')}_fill"
        if stroke:
            return f"layer_{stroke.replace('#', '')}_stroke"
        return f"layer_{index}_unnamed"
    # strategy == "order"
    if index == 1:
        return "layer_1_background"
    if index == 2:
        return "layer_2_mid"
    if index == 3:
        return "layer_3_foreground"
    return f"layer_{index}"


def name_svg_layers(svg_path: Path, strategy: str = "color") -> Path:
    """Add meaningful ``id`` and Inkscape-compatible labels to SVG groups and paths.

    Parameters
    ----------
    svg_path:
        Path to the SVG file to modify (in-place).
    strategy:
        ``"color"`` names layers after their dominant fill/stroke color.
        ``"order"`` names them by stacking order (background, mid, foreground).

    Returns
    -------
    The *svg_path* that was passed in.
    """
    svg_path = Path(svg_path)
    if strategy not in {"color", "order"}:
        raise ValueError("strategy must be 'color' or 'order'.")

    try:
        tree = ET.parse(svg_path)
    except ET.ParseError:
        return svg_path

    root = tree.getroot()
    counter = 0

    # Walk depth-first so visual order roughly matches DOM order.
    for elem in root.iter():
        tag = _get_local_name(elem.tag)
        if tag not in {"g", "path", "polygon", "rect", "circle"}:
            continue
        counter += 1
        colors = _extract_colors_from_element(elem)
        name = _make_layer_name(counter, colors, strategy)
        elem.set("id", name)
        elem.set(f"{{{_INKSCAPE_NS}}}label", name)
        # Mark as non-sensitive so Inkscape treats it as a regular layer.
        elem.set(f"{{{_SODIPODI_NS}}}insensitive", "false")

    # Preserve the XML declaration and write back.
    tree.write(svg_path, encoding="utf-8", xml_declaration=True)
    return svg_path


def analyze_svg_structure(svg_path: Path) -> dict[str, Any]:
    """Deep-parse an SVG and return a tree-shaped description.

    The returned dictionary contains view-box info, a flat list of layer
    descriptors, totals, and the color palette.
    """
    svg_path = Path(svg_path)
    result: dict[str, Any] = {
        "viewBox": None,
        "width": None,
        "height": None,
        "layers": [],
        "total_paths": 0,
        "total_groups": 0,
        "color_palette": [],
    }

    try:
        tree = ET.parse(svg_path)
    except ET.ParseError:
        return result

    root = tree.getroot()
    result["viewBox"] = root.get("viewBox")
    result["width"] = root.get("width")
    result["height"] = root.get("height")

    palette: set[str] = set()

    for elem in root.iter():
        tag = _get_local_name(elem.tag)
        if tag == "svg":
            continue
        if tag == "path":
            result["total_paths"] += 1
        elif tag == "g":
            result["total_groups"] += 1

        if tag not in {"g", "path", "polygon", "rect", "circle"}:
            continue

        colors = _extract_colors_from_element(elem)
        fill = colors.get("fill")
        stroke = colors.get("stroke")
        if fill:
            palette.add(fill)
        if stroke:
            palette.add(stroke)

        bbox: list[float] | None = None
        if tag == "path":
            bbox = _bbox_from_path_d(elem.get("d"))
        elif tag == "rect":
            bbox = _bbox_from_rect(elem)
        elif tag == "polygon":
            bbox = _bbox_from_polygon(elem.get("points"))

        # Count child paths inside groups
        path_count = 0
        if tag == "g":
            path_count = sum(1 for child in elem.iter() if _get_local_name(child.tag) == "path")

        layer_name = elem.get("id") or elem.get(f"{{{_INKSCAPE_NS}}}label") or f"unnamed_{tag}"
        result["layers"].append({
            "name": layer_name,
            "type": tag,
            "fill": fill,
            "stroke": stroke,
            "path_count": path_count if tag == "g" else 1,
            "bbox": bbox,
        })

    result["color_palette"] = sorted(palette)
    return result


def extract_color_palette(svg_path: Path) -> tuple[list[str], dict[str, int]]:
    """Extract every color used in *fill*, *stroke*, and *stop-color* attributes.

    Returns
    -------
    A tuple ``(sorted_colors, counts)`` where *counts* maps each normalized color
    to its total number of occurrences.
    """
    svg_path = Path(svg_path)
    text = svg_path.read_text(encoding="utf-8", errors="replace")
    counts = _extract_all_colors(text)
    sorted_colors = sorted(counts.keys(), key=lambda c: (-counts[c], c))
    return sorted_colors, counts


def suggest_optimization(svg_path: Path) -> list[str]:
    """Analyze an SVG and return a list of human-readable optimization hints."""
    svg_path = Path(svg_path)
    suggestions: list[str] = []

    try:
        stats = svg_stats(svg_path)
    except Exception:
        return suggestions

    file_bytes = stats.get("file_bytes", 0)
    paths = stats.get("paths", 0)
    groups = stats.get("groups", 0)

    try:
        sorted_colors, counts = extract_color_palette(svg_path)
        color_count = len(sorted_colors)
    except Exception:
        color_count = 0

    if file_bytes > 100_000:
        suggestions.append("文件较大，建议减少 color_precision")
    if paths > 200:
        suggestions.append("路径数过多，建议增加 filter_speckle")
    if groups > 0 and paths > 0 and paths / groups < 1.5:
        suggestions.append("存在大量单路径图层，建议合并")
    if paths == 0 and groups == 0:
        suggestions.append("SVG 中未检测到可绘制元素")
    if color_count > 64:
        suggestions.append("颜色数过多，建议启用颜色合并")
    if paths > 100:
        suggestions.append("路径数过多，建议启用路径合并")
    if file_bytes > 200_000:
        suggestions.append("文件过大，建议综合优化")

    return suggestions


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


def svg_quality_score(svg_path: Path) -> dict[str, float]:
    """Lightweight wrapper that lazily imports the real scorer to avoid circular imports."""
    from .svg_optimizer import svg_quality_score as _real_score
    return _real_score(svg_path)
