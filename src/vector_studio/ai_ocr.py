from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

try:
    import numpy as np

    _HAS_NUMPY = True
except Exception:  # pragma: no cover
    np = None  # type: ignore[assignment]
    _HAS_NUMPY = False

from PIL import Image, ImageFilter, ImageStat

logger = logging.getLogger(__name__)

_SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", _SVG_NS)


def _to_numpy(img: Image.Image) -> Any:
    """Convert a PIL image to a NumPy array, or raise if NumPy is unavailable."""
    if not _HAS_NUMPY:
        raise RuntimeError("NumPy is required for this operation but is not installed.")
    return np.array(img)


def detect_text_regions(img: Image.Image) -> list[dict]:
    """Detect likely text regions in an image using heuristic analysis.

    Uses contrast analysis, horizontal line density, and aspect-ratio filtering.
    No external OCR library is required.

    Args:
        img: Input PIL image.

    Returns:
        List of region dictionaries, each with ``bbox`` [x, y, w, h] and
        ``confidence`` (0.0-1.0).
    """
    if img.mode != "RGB":
        img = img.convert("RGB")

    w, h = img.size
    if w < 16 or h < 16:
        return []

    gray = img.convert("L")

    # Step 1: high-contrast region detection
    edges = gray.filter(ImageFilter.FIND_EDGES)
    # Threshold to binary edge map
    edge_binary = edges.point(lambda p: 255 if p > 40 else 0)

    # Step 2: horizontal line density analysis
    # Text has many horizontal strokes; compute row-wise edge density
    if _HAS_NUMPY:
        edge_arr = _to_numpy(edge_binary.convert("L")) // 255
        row_density = edge_arr.mean(axis=1)
        col_density = edge_arr.mean(axis=0)
    else:
        pixels = list(edge_binary.getdata())
        row_density = []
        for y in range(h):
            row = [pixels[y * w + x] for x in range(w)]
            row_density.append(sum(row) / (255.0 * w))
        col_density = []
        for x in range(w):
            col = [pixels[y * w + x] for y in range(h)]
            col_density.append(sum(col) / (255.0 * h))

    # Find rows/cols with high density (potential text lines)
    text_rows = [y for y, d in enumerate(row_density) if d > 0.05]
    text_cols = [x for x, d in enumerate(col_density) if d > 0.03]

    if not text_rows or not text_cols:
        return []

    # Group contiguous rows into line bands
    def _group_contiguous(indices: list[int]) -> list[tuple[int, int]]:
        if not indices:
            return []
        groups = []
        start = indices[0]
        prev = indices[0]
        for idx in indices[1:]:
            if idx > prev + 3:  # gap tolerance
                groups.append((start, prev))
                start = idx
            prev = idx
        groups.append((start, prev))
        return groups

    row_groups = _group_contiguous(text_rows)
    col_groups = _group_contiguous(text_cols)

    regions: list[dict] = []
    for y0, y1 in row_groups:
        for x0, x1 in col_groups:
            rw = x1 - x0 + 1
            rh = y1 - y0 + 1
            # Aspect ratio filter: text is typically wide and short
            aspect = rw / rh if rh > 0 else 0
            if rh < 8 or rw < 16:
                continue
            if aspect < 1.0 or aspect > 30.0:
                continue
            # Confidence based on edge density within the region
            if _HAS_NUMPY:
                region_edges = edge_arr[y0 : y1 + 1, x0 : x1 + 1]
                density = float(region_edges.mean())
            else:
                region_pixels = [
                    pixels[y * w + x]
                    for y in range(y0, y1 + 1)
                    for x in range(x0, x1 + 1)
                ]
                density = sum(region_pixels) / (255.0 * len(region_pixels))

            confidence = min(1.0, density * 5.0 + 0.3)
            regions.append({
                "bbox": [int(x0), int(y0), int(rw), int(rh)],
                "confidence": round(confidence, 3),
            })

    # Merge overlapping regions
    regions = _merge_regions(regions)
    return regions


def _merge_regions(regions: list[dict], iou_threshold: float = 0.3) -> list[dict]:
    """Merge overlapping bounding boxes."""
    if not regions:
        return regions

    # Sort by confidence descending
    sorted_regions = sorted(regions, key=lambda r: r["confidence"], reverse=True)
    merged: list[dict] = []

    for region in sorted_regions:
        x, y, w, h = region["bbox"]
        r1 = {"x": x, "y": y, "x2": x + w, "y2": y + h}
        overlaps = False
        for m in merged:
            mx, my, mw, mh = m["bbox"]
            r2 = {"x": mx, "y": my, "x2": mx + mw, "y2": my + mh}
            inter_x = max(r1["x"], r2["x"])
            inter_y = max(r1["y"], r2["y"])
            inter_x2 = min(r1["x2"], r2["x2"])
            inter_y2 = min(r1["y2"], r2["y2"])
            inter_w = max(0, inter_x2 - inter_x)
            inter_h = max(0, inter_y2 - inter_y)
            inter_area = inter_w * inter_h
            union_area = w * h + mw * mh - inter_area
            iou = inter_area / union_area if union_area > 0 else 0
            if iou > iou_threshold:
                overlaps = True
                # Expand merged box to include this region
                new_x = min(r1["x"], r2["x"])
                new_y = min(r1["y"], r2["y"])
                new_x2 = max(r1["x2"], r2["x2"])
                new_y2 = max(r1["y2"], r2["y2"])
                m["bbox"] = [new_x, new_y, new_x2 - new_x, new_y2 - new_y]
                m["confidence"] = max(m["confidence"], region["confidence"])
                break
        if not overlaps:
            merged.append(region)

    return merged


def recognize_text(img: Image.Image, regions: list[dict] | None = None) -> list[dict]:
    """Recognize text in an image, optionally using pre-detected regions.

    Tries ``pytesseract`` first, then ``easyocr`` if available.
    If no OCR library is installed, returns regions with empty ``text`` fields.

    Args:
        img: Input PIL image.
        regions: Optional pre-detected text regions. If None, ``detect_text_regions``
            is called first.

    Returns:
        List of region dictionaries with ``text``, ``bbox``, and ``confidence``.
    """
    if img.mode != "RGB":
        img = img.convert("RGB")

    if regions is None:
        regions = detect_text_regions(img)

    # Try pytesseract first
    ocr_results: list[dict] = []
    try:
        import pytesseract

        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        n_boxes = len(data["text"])
        for i in range(n_boxes):
            text = data["text"][i].strip()
            if not text:
                continue
            conf = int(data["conf"][i])
            if conf < 30:
                continue
            x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
            ocr_results.append({
                "text": text,
                "bbox": [x, y, w, h],
                "confidence": conf / 100.0,
            })
        return ocr_results
    except ImportError:
        pass
    except Exception as exc:
        logger.debug("pytesseract failed: %s", exc)

    # Try easyocr
    try:
        import easyocr

        reader = easyocr.Reader(["en"], gpu=False)
        results = reader.readtext(_to_numpy(img))
        for r in results:
            bbox_points, text, conf = r
            xs = [p[0] for p in bbox_points]
            ys = [p[1] for p in bbox_points]
            x, y = int(min(xs)), int(min(ys))
            w = int(max(xs) - x)
            h = int(max(ys) - y)
            ocr_results.append({
                "text": text,
                "bbox": [x, y, w, h],
                "confidence": float(conf),
            })
        return ocr_results
    except ImportError:
        pass
    except Exception as exc:
        logger.debug("easyocr failed: %s", exc)

    # Fallback: return heuristic regions without text content
    for region in regions:
        region["text"] = ""
    return regions


def create_text_overlay_svg(text_regions: list[dict], svg_size: tuple[int, int]) -> str:
    """Generate SVG ``<text>`` elements from recognized text regions.

    Estimates font size from region height. Uses a generic sans-serif font family.

    Args:
        text_regions: List of region dicts with ``text``, ``bbox`` [x, y, w, h].
        svg_size: (width, height) of the target SVG canvas.

    Returns:
        SVG text fragment string (one or more ``<text>`` elements).
    """
    if not text_regions:
        return ""

    sw, sh = svg_size
    fragments: list[str] = []
    for region in text_regions:
        text = region.get("text", "")
        if not text:
            continue
        x, y, w, h = region["bbox"]
        # Estimate font size: roughly 70% of box height
        font_size = max(8, int(h * 0.7))
        # Clamp to box width (very rough heuristic)
        max_chars = max(1, w // (font_size // 2))
        display_text = text if len(text) <= max_chars else text[: max_chars - 1] + "..."
        # Escape XML entities
        display_text = display_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        fragments.append(
            f'  <text x="{x}" y="{y + h}" font-size="{font_size}" '
            f'font-family="sans-serif" fill="#000000" text-anchor="start">{display_text}</text>'
        )

    return "\n".join(fragments)


def integrate_text_to_svg(svg_path: Path, text_regions: list[dict], output_path: Path) -> Path:
    """Insert recognized text as editable ``<text>`` elements into an SVG.

    The text layer is placed at the end of the SVG so it renders on top.

    Args:
        svg_path: Path to the original SVG file.
        text_regions: List of region dicts with ``text`` and ``bbox``.
        output_path: Path to write the modified SVG.

    Returns:
        Path to the modified SVG file.
    """
    svg_path = Path(svg_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    text = svg_path.read_text(encoding="utf-8")

    # Extract viewBox or width/height for scaling
    viewbox_match = re.search(r'viewBox="([^"]+)"', text)
    width_match = re.search(r'width="([^"]+)"', text)
    height_match = re.search(r'height="([^"]+)"', text)

    if viewbox_match:
        parts = viewbox_match.group(1).split()
        if len(parts) == 4:
            svg_size = (int(float(parts[2])), int(float(parts[3])))
        else:
            svg_size = (100, 100)
    elif width_match and height_match:
        try:
            svg_size = (int(float(width_match.group(1))), int(float(height_match.group(1))))
        except ValueError:
            svg_size = (100, 100)
    else:
        svg_size = (100, 100)

    overlay = create_text_overlay_svg(text_regions, svg_size)
    if not overlay:
        # No text to add; just copy if paths differ
        if output_path != svg_path:
            output_path.write_text(text, encoding="utf-8")
        return output_path

    # Insert before the closing </svg> tag
    # Handle both <svg ...>...</svg> and self-closing edge cases
    svg_end = text.rfind("</svg>")
    if svg_end == -1:
        # Malformed SVG: append overlay and closing tag
        text = text.rstrip() + "\n" + overlay + "\n</svg>\n"
    else:
        text = text[:svg_end] + overlay + "\n" + text[svg_end:]

    output_path.write_text(text, encoding="utf-8")
    return output_path
