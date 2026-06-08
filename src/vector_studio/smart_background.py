from __future__ import annotations

import math
from pathlib import Path
from typing import Any

try:
    import numpy as np

    _HAS_NUMPY = True
except Exception:  # pragma: no cover
    np = None  # type: ignore[assignment]
    _HAS_NUMPY = False

from PIL import Image, ImageFilter, ImageOps


def _to_numpy(img: Image.Image) -> Any:
    """Convert a PIL image to a NumPy array, or raise if NumPy is unavailable."""
    if not _HAS_NUMPY:
        raise RuntimeError("NumPy is required for this operation but is not installed.")
    return np.array(img)


def _from_numpy(arr: Any, mode: str) -> Image.Image:
    """Convert a NumPy array back to a PIL image."""
    if not _HAS_NUMPY:
        raise RuntimeError("NumPy is required for this operation but is not installed.")
    # Pillow >=10 deprecates the mode kwarg for fromarray; infer from shape.
    return Image.fromarray(arr.astype(np.uint8))


def _clamp(value: float, low: float = 0.0, high: float = 255.0) -> int:
    return int(max(low, min(high, value)))


# ---------------------------------------------------------------------------
# smart_background
# ---------------------------------------------------------------------------

def detect_background_color(img: Image.Image) -> str | None:
    """Detect the most likely background color by sampling border pixels.

    Samples the four corners and a strip along each edge, then clusters
    colors to find the dominant background candidate. Returns a hex string
    like ``#ffffff``, or ``None`` if the image already has an alpha channel.

    Args:
        img: A PIL ``Image`` instance.

    Returns:
        Hex color string or ``None``.
    """
    if img.mode in {"RGBA", "LA", "PA"}:
        # If there is already transparency, we assume the caller wants to keep it.
        return None

    rgb = img.convert("RGB")
    w, h = rgb.size
    if w < 4 or h < 4:
        # Too small to sample meaningfully; fall back to top-left pixel.
        r, g, b = rgb.getpixel((0, 0))
        return f"#{r:02x}{g:02x}{b:02x}"

    # Collect border pixels: corners + edge strips.
    pixels: list[tuple[int, int, int]] = []
    strip = max(1, min(w, h) // 20)

    # Top and bottom edges
    for x in range(0, w, max(1, w // strip)):
        pixels.append(rgb.getpixel((x, 0)))
        pixels.append(rgb.getpixel((x, h - 1)))
    # Left and right edges
    for y in range(0, h, max(1, h // strip)):
        pixels.append(rgb.getpixel((0, y)))
        pixels.append(rgb.getpixel((w - 1, y)))
    # Four corners (already partially covered, but reinforce)
    for corner in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        pixels.append(rgb.getpixel(corner))

    # Simple clustering by rounding to nearest multiple of 16.
    buckets: dict[tuple[int, int, int], list[tuple[int, int, int]]] = {}
    for r, g, b in pixels:
        key = ((r // 16) * 16, (g // 16) * 16, (b // 16) * 16)
        buckets.setdefault(key, []).append((r, g, b))

    if not buckets:
        return "#ffffff"

    # Pick the bucket with the most samples.
    best_bucket = max(buckets, key=lambda k: len(buckets[k]))
    # Return the average color of that bucket for accuracy.
    colors = buckets[best_bucket]
    avg_r = round(sum(c[0] for c in colors) / len(colors))
    avg_g = round(sum(c[1] for c in colors) / len(colors))
    avg_b = round(sum(c[2] for c in colors) / len(colors))
    return f"#{avg_r:02x}{avg_g:02x}{avg_b:02x}"


def remove_background(
    input_path: Path,
    output_path: Path,
    tolerance: int = 30,
) -> Path:
    """Remove a uniform background from an image and save as transparent PNG.

    Uses the detected background color plus a Euclidean distance threshold
    to decide which pixels become transparent. Edge pixels receive a smooth
    alpha gradient for anti-aliasing.

    Args:
        input_path: Path to the source raster image.
        output_path: Path where the transparent PNG will be written.
        tolerance: Maximum RGB distance (0-255) from the background color to
            treat a pixel as background.

    Returns:
        The ``output_path``.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(input_path) as img:
        img = ImageOps.exif_transpose(img)
        rgb = img.convert("RGB")
        bg_hex = detect_background_color(rgb)
        if bg_hex is None:
            # Already has alpha; just save as-is.
            img.save(output_path, format="PNG", optimize=True)
            return output_path

        bg = _hex_to_rgb(bg_hex)
        w, h = rgb.size
        rgba = Image.new("RGBA", (w, h))

        # Build alpha mask with anti-aliased edges.
        if _HAS_NUMPY:
            arr = _to_numpy(rgb)
            diff = np.linalg.norm(arr.astype(np.float32) - np.array(bg, dtype=np.float32), axis=2)
            alpha = np.clip(255 * (diff - tolerance / 2) / max(tolerance / 2, 1), 0, 255)
            alpha = alpha.astype(np.uint8)
            rgba_arr = np.dstack((arr, alpha))
            rgba = _from_numpy(rgba_arr, "RGBA")
        else:
            # Pure-PIL fallback (slower but zero extra dependencies).
            for y in range(h):
                for x in range(w):
                    r, g, b = rgb.getpixel((x, y))
                    dist = math.sqrt((r - bg[0]) ** 2 + (g - bg[1]) ** 2 + (b - bg[2]) ** 2)
                    if dist <= tolerance:
                        a = 0
                    elif dist >= tolerance * 2:
                        a = 255
                    else:
                        a = int(255 * (dist - tolerance) / tolerance)
                    rgba.putpixel((x, y), (r, g, b, _clamp(a)))

        rgba.save(output_path, format="PNG", optimize=True)

    return output_path


def is_likely_logo(img: Image.Image) -> tuple[bool, str]:
    """Heuristically decide whether an image looks like a logo or icon.

    Considers color count, presence of a central subject, uniform edge
    background, and aspect ratio.

    Args:
        img: A PIL ``Image`` instance.

    Returns:
        ``(is_likely, reason)`` tuple.
    """
    rgb = img.convert("RGB")
    w, h = rgb.size

    # 1. Actual color count (quantized to reduce noise).
    small = rgb.resize((max(1, w // 4), max(1, h // 4)), Image.Resampling.NEAREST)
    quantized = small.quantize(colors=16, method=Image.Quantize.MEDIANCUT)
    color_count = len(quantized.getcolors())

    # 2. Edge background uniformity: require >60% of edge pixels match bg.
    bg_hex = detect_background_color(rgb)
    if bg_hex is not None:
        bg = _hex_to_rgb(bg_hex)
        edge_pixels: list[tuple[int, int, int]] = []
        for x in range(w):
            edge_pixels.append(rgb.getpixel((x, 0)))
            edge_pixels.append(rgb.getpixel((x, h - 1)))
        for y in range(h):
            edge_pixels.append(rgb.getpixel((0, y)))
            edge_pixels.append(rgb.getpixel((w - 1, y)))
        matching = sum(
            1
            for r, g, b in edge_pixels
            if abs(r - bg[0]) <= 32 and abs(g - bg[1]) <= 32 and abs(b - bg[2]) <= 32
        )
        edge_uniform = matching / max(len(edge_pixels), 1) > 0.6
    else:
        edge_uniform = False

    # 3. Aspect ratio near 1:1 (common for icons).
    aspect_ratio = max(w, h) / max(min(w, h), 1)
    near_square = aspect_ratio <= 1.3

    # 4. Central subject: compare center color variance vs edge.
    center_box = rgb.crop((w // 4, h // 4, 3 * w // 4, 3 * h // 4))
    center_small = center_box.resize((max(1, w // 8), max(1, h // 8)), Image.Resampling.NEAREST)
    center_colors = center_small.quantize(colors=8, method=Image.Quantize.MEDIANCUT)
    center_color_count = len(center_colors.getcolors())
    has_center_subject = center_color_count >= 2

    score = 0
    reasons: list[str] = []
    if color_count < 8:
        score += 1
        reasons.append(f"few colors ({color_count})")
    if edge_uniform:
        score += 1
        reasons.append("uniform edge background")
    if near_square:
        score += 1
        reasons.append("near-square aspect ratio")
    if has_center_subject:
        score += 1
        reasons.append("distinct center subject")

    is_likely = score >= 3
    reason = (
        f"Logo-like ({', '.join(reasons)})"
        if is_likely
        else f"Not logo-like ({', '.join(reasons)})"
    )
    return is_likely, reason


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.strip()
    if value.startswith("#"):
        value = value[1:]
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        raise ValueError("Color must be a hex string like #ffffff.")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
