from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .svg_tools import (
    _extract_all_colors,
    _extract_colors_from_element,
    _get_local_name,
    _parse_color,
    optimize_svg_file,
    optimize_svg_text,
    svg_stats,
)

_SVG_NS = "http://www.w3.org/2000/svg"

# Register namespace so ElementTree writes it with proper prefix.
ET.register_namespace("", _SVG_NS)

# Regex for path data commands and numbers
_PATH_COMMAND_RE = re.compile(r"([MmLlHhVvCcSsQqTtAaZz])")
_PATH_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")


def _copy_or_overwrite(svg_path: Path, output_path: Path | None) -> Path:
    """Return the path that will be written to.

    If *output_path* is None, modify *svg_path* in-place.
    Otherwise write to *output_path* (copying first if different from *svg_path*).
    """
    svg_path = Path(svg_path)
    if output_path is None:
        return svg_path
    output_path = Path(output_path)
    if output_path.resolve() != svg_path.resolve():
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(svg_path.read_text(encoding="utf-8"), encoding="utf-8")
    return output_path


def _normalize_path_d(d: str) -> str:
    """Return a cleaned *d* string with single spaces and no leading/trailing spaces."""
    d = d.replace(",", " ")
    d = _PATH_COMMAND_RE.sub(r" \1 ", d)
    d = " ".join(d.split())
    return d.strip()


def _tokenize_path_d(d: str) -> list[str]:
    """Tokenize path data into a list of commands and numbers."""
    d = _normalize_path_d(d)
    tokens: list[str] = []
    i = 0
    while i < len(d):
        if d[i] in "MmLlHhVvCcSsQqTtAaZz":
            tokens.append(d[i])
            i += 1
        elif d[i].isspace():
            i += 1
        else:
            # number
            match = _PATH_NUMBER_RE.match(d, i)
            if match:
                tokens.append(match.group(0))
                i = match.end()
            else:
                i += 1
    return tokens


def _reduce_decimals(token: str, places: int) -> str:
    """Reduce decimal places in a numeric token."""
    try:
        val = float(token)
    except ValueError:
        return token
    if places <= 0:
        return str(int(round(val)))
    fmt = f"{{:.{places}f}}"
    result = fmt.format(val).rstrip("0").rstrip(".")
    return result if result else "0"


def _merge_path_ds(ds: list[str]) -> str:
    """Merge multiple path *d* strings into one, separating with ``M`` commands."""
    parts: list[str] = []
    for d in ds:
        d = d.strip()
        if not d:
            continue
        # Ensure each subpath starts with M/m
        tokens = _tokenize_path_d(d)
        if not tokens:
            continue
        if tokens[0] not in "Mm":
            parts.append("M 0 0 " + d)
        else:
            parts.append(d)
    return " ".join(parts)


def merge_same_color_paths(svg_path: Path, output_path: Path | None = None) -> Path:
    """Merge ``<path>`` elements that share the same *fill* color.

    The *d* attributes are concatenated with ``M`` separators so the visual
    result is preserved (VTracer output is typically non-overlapping).

    Parameters
    ----------
    svg_path:
        Input SVG file.
    output_path:
        If given, write the result to this path; otherwise modify *svg_path* in-place.

    Returns
    -------
    The path that was written to.
    """
    target = _copy_or_overwrite(svg_path, output_path)

    try:
        tree = ET.parse(target)
    except ET.ParseError:
        return target

    root = tree.getroot()

    # Collect paths grouped by normalized fill color.
    color_groups: dict[str, list[ET.Element]] = {}
    for elem in root.iter():
        if _get_local_name(elem.tag) != "path":
            continue
        colors = _extract_colors_from_element(elem)
        fill = colors.get("fill") or "none"
        color_groups.setdefault(fill, []).append(elem)

    # For each color group with >1 path, merge them.
    for fill, elems in color_groups.items():
        if len(elems) <= 1:
            continue
        ds = [e.get("d", "") for e in elems]
        merged_d = _merge_path_ds(ds)
        # Keep the first element as the merged path, remove the rest.
        first = elems[0]
        first.set("d", merged_d)
        # Ensure fill is explicit and consistent.
        if fill != "none":
            first.set("fill", fill)
            first.attrib.pop("style", None)
        for e in elems[1:]:
            parent = _find_parent(root, e)
            if parent is not None:
                parent.remove(e)

    tree.write(target, encoding="utf-8", xml_declaration=True)
    return target


def _find_parent(root: ET.Element, child: ET.Element) -> ET.Element | None:
    """Return the parent element of *child* inside *root*, or None."""
    for parent in root.iter():
        for c in parent:
            if c is child:
                return parent
    return None


def _color_distance(c1: str, c2: str) -> float:
    """Compute Euclidean distance between two ``#rrggbb`` colors."""
    def _to_rgb(c: str) -> tuple[int, int, int]:
        c = c.lstrip("#")
        return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)

    r1, g1, b1 = _to_rgb(c1)
    r2, g2, b2 = _to_rgb(c2)
    return math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2)


def _quantize_colors(colors: list[str], threshold: int) -> dict[str, str]:
    """Map each color to a representative color using simple greedy bucketing.

    Colors are processed in descending frequency order so the most common
    colors become the bucket representatives.
    """
    if not colors:
        return {}

    # Count frequencies
    counts: dict[str, int] = {}
    for c in colors:
        counts[c] = counts.get(c, 0) + 1

    sorted_colors = sorted(counts.keys(), key=lambda c: (-counts[c], c))
    buckets: list[list[str]] = []
    representatives: list[str] = []

    for color in sorted_colors:
        placed = False
        for rep, bucket in zip(representatives, buckets):
            if _color_distance(color, rep) <= threshold:
                bucket.append(color)
                placed = True
                break
        if not placed:
            representatives.append(color)
            buckets.append([color])

    mapping: dict[str, str] = {}
    for rep, bucket in zip(representatives, buckets):
        for c in bucket:
            mapping[c] = rep
    return mapping


def merge_similar_colors(
    svg_path: Path, output_path: Path | None = None, threshold: int = 10
) -> Path:
    """Quantize colors by merging similar fills (RGB distance < *threshold*).

    Parameters
    ----------
    svg_path:
        Input SVG file.
    output_path:
        If given, write the result to this path; otherwise modify *svg_path* in-place.
    threshold:
        Maximum Euclidean RGB distance for two colors to be considered similar.

    Returns
    -------
    The path that was written to.
    """
    target = _copy_or_overwrite(svg_path, output_path)

    try:
        tree = ET.parse(target)
    except ET.ParseError:
        return target

    root = tree.getroot()

    # Gather all fill colors from path elements.
    all_fills: list[str] = []
    path_elems: list[ET.Element] = []
    for elem in root.iter():
        if _get_local_name(elem.tag) != "path":
            continue
        colors = _extract_colors_from_element(elem)
        fill = colors.get("fill")
        if fill:
            all_fills.append(fill)
            path_elems.append(elem)

    if not all_fills:
        return target

    color_map = _quantize_colors(all_fills, threshold)

    # Update elements.
    for elem in path_elems:
        colors = _extract_colors_from_element(elem)
        fill = colors.get("fill")
        if fill and fill in color_map:
            new_fill = color_map[fill]
            elem.set("fill", new_fill)
            # Remove inline style fill to avoid conflict.
            style = elem.get("style", "")
            if style:
                parts = [p for p in style.split(";") if p.strip().lower().startswith("fill") is False]
                if parts:
                    elem.set("style", ";".join(parts))
                else:
                    elem.attrib.pop("style", None)

    tree.write(target, encoding="utf-8", xml_declaration=True)
    return target


def simplify_path_data(
    svg_path: Path, output_path: Path | None = None, tolerance: float = 0.5
) -> Path:
    """Simplify path *d* attributes.

    Simplifications applied:

    1. Reduce decimal places based on *tolerance*.
    2. Collapse consecutive ``L`` (or ``l``) segments that are shorter than
       *tolerance* into the next point.
    3. Remove redundant whitespace.

    Parameters
    ----------
    svg_path:
        Input SVG file.
    output_path:
        If given, write the result to this path; otherwise modify *svg_path* in-place.
    tolerance:
        Controls simplification aggressiveness. Higher = more aggressive.

    Returns
    -------
    The path that was written to.
    """
    target = _copy_or_overwrite(svg_path, output_path)

    try:
        tree = ET.parse(target)
    except ET.ParseError:
        return target

    root = tree.getroot()

    # Determine decimal places from tolerance (e.g. tolerance 0.5 -> 0 places, 0.1 -> 1 place)
    places = max(0, int(-math.log10(tolerance + 1e-9)))

    for elem in root.iter():
        if _get_local_name(elem.tag) != "path":
            continue
        d = elem.get("d", "")
        if not d:
            continue
        simplified = _simplify_d(d, tolerance, places)
        elem.set("d", simplified)

    tree.write(target, encoding="utf-8", xml_declaration=True)
    return target


def _simplify_d(d: str, tolerance: float, places: int) -> str:
    """Simplify a single path *d* string."""
    tokens = _tokenize_path_d(d)
    if not tokens:
        return d

    result: list[str] = []
    i = 0
    current_cmd: str | None = None
    current_pos = (0.0, 0.0)
    subpath_start = (0.0, 0.0)

    while i < len(tokens):
        token = tokens[i]
        if token in "MmLlHhVvCcSsQqTtAaZz":
            current_cmd = token
            result.append(token)
            i += 1
            if token in "Zz":
                current_pos = subpath_start
            continue

        # Parse command arguments
        if current_cmd is None:
            i += 1
            continue

        cmd = current_cmd
        # Read arguments based on command
        if cmd in "MmLlTt":
            if i + 1 >= len(tokens):
                break
            x = float(tokens[i])
            y = float(tokens[i + 1])
            i += 2
            if cmd in "Mm":
                if cmd == "M":
                    current_pos = (x, y)
                    subpath_start = current_pos
                else:
                    current_pos = (current_pos[0] + x, current_pos[1] + y)
                    subpath_start = current_pos
                result.append(_reduce_decimals(str(x), places))
                result.append(_reduce_decimals(str(y), places))
            elif cmd in "Ll":
                abs_cmd = cmd == "L"
                nx = x if abs_cmd else current_pos[0] + x
                ny = y if abs_cmd else current_pos[1] + y
                dx = nx - current_pos[0]
                dy = ny - current_pos[1]
                seg_len = math.hypot(dx, dy)
                if seg_len < tolerance and len(result) > 1 and result[-1] not in "ZzMm":
                    # Skip this short segment: replace last point with new point
                    # Pop last two numbers and push new point
                    if len(result) >= 2:
                        # Check if previous command was L/l
                        prev_cmd_idx = _last_command_index(result)
                        if prev_cmd_idx is not None and result[prev_cmd_idx] in "Ll":
                            result.pop()
                            result.pop()
                            result.append(_reduce_decimals(str(x if abs_cmd else nx), places))
                            result.append(_reduce_decimals(str(y if abs_cmd else ny), places))
                            current_pos = (nx, ny)
                            continue
                result.append(_reduce_decimals(str(x), places))
                result.append(_reduce_decimals(str(y), places))
                current_pos = (nx, ny)
            elif cmd in "Tt":
                result.append(_reduce_decimals(str(x), places))
                result.append(_reduce_decimals(str(y), places))
                current_pos = (x if cmd == "T" else current_pos[0] + x, y if cmd == "T" else current_pos[1] + y)
        elif cmd in "Hh":
            if i >= len(tokens):
                break
            x = float(tokens[i])
            i += 1
            result.append(_reduce_decimals(str(x), places))
            current_pos = (x if cmd == "H" else current_pos[0] + x, current_pos[1])
        elif cmd in "Vv":
            if i >= len(tokens):
                break
            y = float(tokens[i])
            i += 1
            result.append(_reduce_decimals(str(y), places))
            current_pos = (current_pos[0], y if cmd == "V" else current_pos[1] + y)
        elif cmd in "Cc":
            if i + 5 >= len(tokens):
                break
            coords = [float(tokens[j]) for j in range(i, i + 6)]
            i += 6
            for c in coords:
                result.append(_reduce_decimals(str(c), places))
            if cmd == "C":
                current_pos = (coords[4], coords[5])
            else:
                current_pos = (current_pos[0] + coords[4], current_pos[1] + coords[5])
        elif cmd in "SsQq":
            if i + 3 >= len(tokens):
                break
            coords = [float(tokens[j]) for j in range(i, i + 4)]
            i += 4
            for c in coords:
                result.append(_reduce_decimals(str(c), places))
            if cmd in "Qq":
                if cmd == "Q":
                    current_pos = (coords[2], coords[3])
                else:
                    current_pos = (current_pos[0] + coords[2], current_pos[1] + coords[3])
            else:
                if cmd == "S":
                    current_pos = (coords[2], coords[3])
                else:
                    current_pos = (current_pos[0] + coords[2], current_pos[1] + coords[3])
        elif cmd in "Aa":
            if i + 6 >= len(tokens):
                break
            coords = [float(tokens[j]) for j in range(i, i + 7)]
            i += 7
            for c in coords:
                result.append(_reduce_decimals(str(c), places))
            if cmd == "A":
                current_pos = (coords[5], coords[6])
            else:
                current_pos = (current_pos[0] + coords[5], current_pos[1] + coords[6])
        else:
            i += 1

    # Post-process: collapse consecutive L commands
    return _collapse_consecutive_l(result, places)


def _last_command_index(tokens: list[str]) -> int | None:
    """Return the index of the last path command token, or None."""
    for idx in range(len(tokens) - 1, -1, -1):
        if tokens[idx] in "MmLlHhVvCcSsQqTtAaZz":
            return idx
    return None


def _collapse_consecutive_l(tokens: list[str], places: int) -> str:
    """Collapse redundant consecutive ``L`` commands into one."""
    result: list[str] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token in "Ll" and len(result) >= 1:
            # If previous token was also L/l with the same case, just append numbers
            prev_cmd_idx = _last_command_index(result)
            if prev_cmd_idx is not None and result[prev_cmd_idx] == token:
                # Skip redundant command letter
                pass
            else:
                result.append(token)
        else:
            result.append(token)
        i += 1
    return " ".join(result)


def svg_quality_score(svg_path: Path) -> dict[str, float]:
    """Compute a comprehensive quality/efficiency score for an SVG.

    Scores are in the range ``0..100`` where higher is better.

    Dimensions
    ----------
    file_size_score:
        Smaller files score higher (< 50 KB = 100).
    path_efficiency:
        Ratio of path count to color count; closer to 1 is better.
    complexity_score:
        Fewer paths score higher (< 50 = 100).
    color_efficiency:
        Fewer colors score higher, but at least 2 are expected for non-trivial images.
    overall:
        Weighted average of the above.
    """
    svg_path = Path(svg_path)
    try:
        stats = svg_stats(svg_path)
    except Exception:
        return {
            "file_size_score": 0.0,
            "path_efficiency": 0.0,
            "complexity_score": 0.0,
            "color_efficiency": 0.0,
            "overall": 0.0,
        }

    file_bytes = stats.get("file_bytes", 0)
    paths = stats.get("paths", 0)

    try:
        sorted_colors, counts = _extract_all_colors(svg_path.read_text(encoding="utf-8", errors="replace"))
        color_count = len(sorted_colors)
    except Exception:
        color_count = 0

    # File size score: <50KB = 100, >500KB = 0, linear in between
    file_size_score = max(0.0, min(100.0, 100.0 - (file_bytes - 50_000) / 4_500))
    if file_bytes <= 50_000:
        file_size_score = 100.0

    # Path efficiency: ideal is 1 path per color (or 1 if monochrome)
    ideal_paths = max(1, color_count)
    if paths > 0:
        ratio = paths / ideal_paths
        # ratio 1 -> 100, ratio 5 -> 0
        path_efficiency = max(0.0, min(100.0, 100.0 - (ratio - 1.0) * 25.0))
    else:
        path_efficiency = 0.0

    # Complexity score: <50 paths = 100, >500 = 0
    complexity_score = max(0.0, min(100.0, 100.0 - (paths - 50) / 4.5))
    if paths <= 50:
        complexity_score = 100.0

    # Color efficiency: 2-16 colors is ideal range
    if color_count == 0:
        color_efficiency = 50.0
    elif color_count <= 16:
        color_efficiency = 100.0 - (color_count - 2) * 2.0
    else:
        color_efficiency = max(0.0, 100.0 - (color_count - 16) * 3.0)

    overall = (
        file_size_score * 0.25
        + path_efficiency * 0.25
        + complexity_score * 0.25
        + color_efficiency * 0.25
    )

    return {
        "file_size_score": round(file_size_score, 2),
        "path_efficiency": round(path_efficiency, 2),
        "complexity_score": round(complexity_score, 2),
        "color_efficiency": round(color_efficiency, 2),
        "overall": round(overall, 2),
    }


def optimize_svg_comprehensive(
    svg_path: Path, output_path: Path | None = None, aggressive: bool = False
) -> Path:
    """Run a comprehensive optimization pipeline on an SVG.

    Steps:

    1. Conservative text cleanup (:func:`optimize_svg_file`).
    2. Merge paths with identical fill colors.
    3. Merge similar colors (more aggressive when *aggressive* is True).
    4. Simplify path data.
    5. Re-run conservative cleanup.

    Parameters
    ----------
    svg_path:
        Input SVG file.
    output_path:
        If given, write the result to this path; otherwise modify *svg_path* in-place.
    aggressive:
        When ``True``, use a larger color-merge threshold and higher path-data
        simplification tolerance.

    Returns
    -------
    The path that was written to.
    """
    target = _copy_or_overwrite(svg_path, output_path)

    # Step 1: basic cleanup
    optimize_svg_file(target)

    # Step 2: merge same-color paths
    merge_same_color_paths(target)

    # Step 3: merge similar colors
    color_threshold = 30 if aggressive else 10
    merge_similar_colors(target, threshold=color_threshold)

    # Step 4: simplify path data
    tolerance = 1.5 if aggressive else 0.5
    simplify_path_data(target, tolerance=tolerance)

    # Step 5: final cleanup
    optimize_svg_file(target)

    return target
