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

from PIL import Image, ImageFilter, ImageStat

from .smart_background import detect_background_color, is_likely_logo


def _to_numpy(img: Image.Image) -> Any:
    if not _HAS_NUMPY:
        raise RuntimeError("NumPy is required for this operation but is not installed.")
    return np.array(img)


# ---------------------------------------------------------------------------
# Feature analysis
# ---------------------------------------------------------------------------

def analyze_image_features(input_path: Path) -> dict[str, Any]:
    """Extract a feature vector from a raster image for preset recommendation.

    Args:
        input_path: Path to the image file.

    Returns:
        Dictionary of computed features. If analysis fails, sensible defaults
        are returned so the caller never crashes.
    """
    input_path = Path(input_path)
    defaults: dict[str, Any] = {
        "width": 0,
        "height": 0,
        "aspect_ratio": 1.0,
        "color_count": 16,
        "edge_density": 0.0,
        "has_alpha": False,
        "mean_brightness": 128.0,
        "brightness_std": 32.0,
        "mean_saturation": 50.0,
        "text_like_density": 0.0,
        "is_likely_logo": False,
        "logo_reason": "",
    }

    try:
        with Image.open(input_path) as img:
            img = img.convert("RGB") if img.mode != "RGBA" else img
            w, h = img.size
            defaults["width"] = w
            defaults["height"] = h
            defaults["aspect_ratio"] = round(max(w, h) / max(min(w, h), 1), 2)
            defaults["has_alpha"] = img.mode in {"RGBA", "LA", "PA"}

            # Color count (quantized to reduce noise).
            small = img.resize((max(1, w // 4), max(1, h // 4)), Image.Resampling.NEAREST)
            quantized = small.quantize(colors=32, method=Image.Quantize.MEDIANCUT)
            palette = quantized.getpalette()
            defaults["color_count"] = len(palette) // 3 if palette else 32

            # Brightness stats.
            gray = img.convert("L")
            stat = ImageStat.Stat(gray)
            defaults["mean_brightness"] = round(stat.mean[0], 2)
            defaults["brightness_std"] = round(stat.stddev[0], 2)

            # Saturation (approximate from RGB variance).
            if _HAS_NUMPY:
                arr = _to_numpy(img).astype(np.float32)
                # Simple saturation proxy: max - min per pixel, averaged.
                sat_proxy = np.mean(np.max(arr, axis=2) - np.min(arr, axis=2))
                defaults["mean_saturation"] = round(float(sat_proxy), 2)
            else:
                # Fallback using PIL stat on difference channels.
                r, g, b = img.split()
                diff1 = ImageChops.difference(r, g)
                diff2 = ImageChops.difference(g, b)
                defaults["mean_saturation"] = round(
                    (ImageStat.Stat(diff1).mean[0] + ImageStat.Stat(diff2).mean[0]) / 2, 2
                )

            # Edge density.
            edges = gray.filter(ImageFilter.FIND_EDGES)
            if _HAS_NUMPY:
                edge_arr = _to_numpy(edges)
                defaults["edge_density"] = round(float(np.mean(edge_arr)) / 255.0, 3)
            else:
                pixels = list(edges.getdata())
                defaults["edge_density"] = round(
                    sum(pixels) / (255.0 * max(len(pixels), 1)), 3
                )

            # Text-like density: high-contrast small regions.
            if _HAS_NUMPY:
                gray_arr = _to_numpy(gray).astype(np.float32)
                # Local variance via difference from blurred version.
                blurred = gray.filter(ImageFilter.GaussianBlur(radius=2))
                blur_arr = _to_numpy(blurred).astype(np.float32)
                local_diff = np.abs(gray_arr - blur_arr)
                text_mask = (local_diff > 20) & (local_diff < 80)
                defaults["text_like_density"] = round(float(np.mean(text_mask)), 3)
            else:
                defaults["text_like_density"] = 0.0

            # Logo heuristic.
            is_logo, reason = is_likely_logo(img)
            defaults["is_likely_logo"] = is_logo
            defaults["logo_reason"] = reason
    except Exception:
        # Graceful degradation: return defaults on any failure.
        pass

    return defaults


# ---------------------------------------------------------------------------
# Recommendation engine
# ---------------------------------------------------------------------------

def recommend_preset(features: dict[str, Any]) -> tuple[str, float, str]:
    """Recommend a tracing preset based on image features.

    Args:
        features: Feature dictionary produced by ``analyze_image_features``.

    Returns:
        ``(preset_name, confidence, reason)`` tuple.
    """
    color_count = features.get("color_count", 16)
    edge_density = features.get("edge_density", 0.0)
    aspect_ratio = features.get("aspect_ratio", 1.0)
    width = features.get("width", 0)
    height = features.get("height", 0)
    mean_brightness = features.get("mean_brightness", 128.0)
    brightness_std = features.get("brightness_std", 32.0)
    text_like_density = features.get("text_like_density", 0.0)
    is_likely_logo = features.get("is_likely_logo", False)

    # Contrast proxy.
    high_contrast = brightness_std > 40 or mean_brightness < 60 or mean_brightness > 200

    scores: dict[str, float] = {}
    reasons: dict[str, str] = {}

    # bw: very few colors, high contrast.
    if color_count <= 3 and high_contrast:
        scores["bw"] = 0.95
        reasons["bw"] = f"Very few colors ({color_count}) with high contrast"
    else:
        scores["bw"] = max(0.0, 0.5 - color_count * 0.05)
        reasons["bw"] = "Low color count but not strictly monochrome"

    # logo: few colors, sharp edges, near-square, logo heuristic.
    logo_score = 0.0
    logo_reasons: list[str] = []
    if color_count < 8:
        logo_score += 0.3
        logo_reasons.append(f"few colors ({color_count})")
    if edge_density > 0.15:
        logo_score += 0.25
        logo_reasons.append("sharp edges")
    if aspect_ratio <= 1.5:
        logo_score += 0.2
        logo_reasons.append("near-square")
    if is_likely_logo:
        logo_score += 0.25
        logo_reasons.append("logo-like composition")
    scores["logo"] = min(logo_score, 0.95)
    reasons["logo"] = f"Logo candidate: {', '.join(logo_reasons)}" if logo_reasons else "Not a strong logo match"

    # pixel_art: low resolution + blocky colors.
    max_side = max(width, height)
    if max_side > 0 and max_side <= 128 and color_count <= 16 and edge_density < 0.1:
        scores["pixel_art"] = 0.96 if max_side <= 64 else 0.92
        reasons["pixel_art"] = f"Low resolution ({width}x{height}) with block colors"
    else:
        scores["pixel_art"] = max(0.0, 0.4 - max_side / 1000)
        reasons["pixel_art"] = "Resolution too high for pixel art"

    # photo: many colors, moderate edges, large size.
    if color_count >= 12 and edge_density < 0.2 and max_side > 400:
        scores["photo"] = 0.9
        reasons["photo"] = f"Rich colors ({color_count}) with photo-like smoothness"
    else:
        scores["photo"] = max(0.0, color_count / 32 - 0.2)
        reasons["photo"] = "Not enough color variety for a photo preset"

    # poster: medium colors, illustration-like.
    if 4 <= color_count < 12 and edge_density >= 0.1:
        scores["poster"] = 0.85
        reasons["poster"] = f"Illustration-like: {color_count} colors with clear edges"
    else:
        scores["poster"] = max(0.0, 0.5 - abs(color_count - 8) * 0.05)
        reasons["poster"] = "Color/edge balance not typical for poster art"

    # scan: text-like density, low contrast, large size.
    if text_like_density > 0.05 and not high_contrast and max_side > 600:
        scores["scan"] = 0.9
        reasons["scan"] = "Text-like patterns with low contrast (scanned document)"
    else:
        scores["scan"] = max(0.0, text_like_density * 5)
        reasons["scan"] = "Not enough text-like structure for scan preset"

    best = max(scores, key=scores.get)  # type: ignore[arg-type]
    confidence = round(scores[best], 2)
    return best, confidence, reasons[best]


def recommend_for_image(input_path: Path) -> tuple[str, float, str, dict[str, Any]]:
    """Analyze an image and return a preset recommendation.

    Args:
        input_path: Path to the image file.

    Returns:
        ``(preset_name, confidence, reason, features)`` tuple.
    """
    features = analyze_image_features(input_path)
    preset, confidence, reason = recommend_preset(features)
    return preset, confidence, reason, features


# Import needed for the pure-PIL saturation fallback.
from PIL import ImageChops  # noqa: E402
