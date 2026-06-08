from __future__ import annotations

import logging
import math
from typing import Any

try:
    import numpy as np

    _HAS_NUMPY = True
except Exception:  # pragma: no cover
    np = None  # type: ignore[assignment]
    _HAS_NUMPY = False

from PIL import Image, ImageFilter, ImageOps, ImageStat

logger = logging.getLogger(__name__)


def _to_numpy(img: Image.Image) -> Any:
    """Convert a PIL image to a NumPy array, or raise if NumPy is unavailable."""
    if not _HAS_NUMPY:
        raise RuntimeError("NumPy is required for this operation but is not installed.")
    return np.array(img)


def _from_numpy(arr: Any, mode: str) -> Image.Image:
    """Convert a NumPy array back to a PIL image."""
    if not _HAS_NUMPY:
        raise RuntimeError("NumPy is required for this operation but is not installed.")
    return Image.fromarray(arr.astype(np.uint8))


def _edge_mask(img: Image.Image, threshold: int = 30) -> Image.Image:
    """Create a binary edge mask using simple gradient magnitude."""
    gray = img.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    if _HAS_NUMPY:
        arr = _to_numpy(edges)
        mask = (arr > threshold).astype(np.uint8) * 255
        return Image.fromarray(mask)
    else:
        # Pure-PIL fallback: threshold the edge image
        return edges.point(lambda p: 255 if p > threshold else 0)


def _blur_with_edge_preserve(img: Image.Image, radius: int = 2) -> Image.Image:
    """Simulate bilateral filtering using ModeFilter + slight Gaussian blur.

    ModeFilter reduces noise while preserving sharp transitions,
    followed by a very mild Gaussian blur for smoothness.
    """
    mode_filtered = img.filter(ImageFilter.ModeFilter(size=5))
    if radius > 0:
        return mode_filtered.filter(ImageFilter.GaussianBlur(radius=radius))
    return mode_filtered


def _kmeans_quantize(img: Image.Image, k: int = 8, max_iter: int = 10) -> Image.Image:
    """Reduce colors using a lightweight k-means on pixel values.

    Falls back to PIL quantize when NumPy is unavailable.
    """
    if not _HAS_NUMPY:
        # Pure-PIL fallback
        return img.quantize(colors=max(2, min(k, 256)), method=Image.Quantize.MEDIANCUT).convert("RGB")

    arr = _to_numpy(img).astype(np.float32)
    h, w = arr.shape[:2]
    pixels = arr.reshape(-1, 3)

    # Initialize centroids with random pixels (deterministic seed via step)
    step = max(1, len(pixels) // k)
    indices = list(range(0, len(pixels), step))[:k]
    centroids = pixels[indices].copy()

    for _ in range(max_iter):
        # Assign each pixel to nearest centroid
        distances = np.linalg.norm(pixels[:, np.newaxis, :] - centroids[np.newaxis, :, :], axis=2)
        labels = np.argmin(distances, axis=1)

        # Recompute centroids
        new_centroids = np.zeros_like(centroids)
        counts = np.zeros(k, dtype=np.int32)
        for i in range(k):
            mask = labels == i
            if np.any(mask):
                new_centroids[i] = pixels[mask].mean(axis=0)
                counts[i] = mask.sum()
            else:
                # Reinitialize empty cluster
                new_centroids[i] = pixels[np.random.randint(len(pixels))]

        if np.allclose(centroids, new_centroids, atol=1.0):
            break
        centroids = new_centroids

    quantized = centroids[labels].reshape(h, w, 3)
    quantized = np.clip(quantized, 0, 255).astype(np.uint8)
    return _from_numpy(quantized, "RGB")


def semantic_simplify(img: Image.Image, color_clusters: int = 8, edge_preserve: bool = True) -> Image.Image:
    """Simplify a complex photo into an illustration-like image.

    Steps:
        1. Bilateral-like smoothing (ModeFilter + slight Gaussian blur).
        2. Color quantization to ``color_clusters`` dominant colors.
        3. Optional edge preservation mask applied before quantization.
        4. Final light smoothing to remove tiny texture artifacts.

    Args:
        img: Input PIL image.
        color_clusters: Number of dominant colors to keep (2-256).
        edge_preserve: If True, detect edges and protect them during quantization.

    Returns:
        Simplified PIL image in RGB mode.
    """
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Step 1: bilateral-like smoothing
    smoothed = _blur_with_edge_preserve(img, radius=2)

    # Step 2 & 3: edge preservation + quantization
    if edge_preserve:
        edges = _edge_mask(smoothed, threshold=60)
        quantized = _kmeans_quantize(smoothed, k=max(2, min(color_clusters, 256)))
        # Blend quantized with original at edge pixels to preserve boundaries
        if _HAS_NUMPY:
            orig_arr = _to_numpy(smoothed)
            q_arr = _to_numpy(quantized)
            e_arr = _to_numpy(edges.convert("L")) / 255.0
            e_arr = e_arr[:, :, np.newaxis]
            blended = (q_arr * (1 - e_arr) + orig_arr * e_arr).astype(np.uint8)
            result = _from_numpy(blended, "RGB")
        else:
            # PIL composite fallback
            result = Image.composite(smoothed, quantized, edges.convert("L"))
    else:
        result = _kmeans_quantize(smoothed, k=max(2, min(color_clusters, 256)))

    # Step 4: light final smoothing
    result = result.filter(ImageFilter.GaussianBlur(radius=1))
    return result.convert("RGB")


def superpixel_simplify(img: Image.Image, n_segments: int = 100) -> Image.Image:
    """Simplify an image by dividing it into superpixel-like regions.

    Uses a simple grid + color clustering approach without external libraries.
    Each region is filled with its average color.

    Args:
        img: Input PIL image.
        n_segments: Target number of segments (approximate).

    Returns:
        Simplified PIL image in RGB mode.
    """
    if img.mode != "RGB":
        img = img.convert("RGB")

    w, h = img.size
    # Compute grid size to approximate n_segments
    aspect = w / h
    n_cols = int(math.sqrt(n_segments * aspect))
    n_rows = int(n_segments / n_cols) if n_cols > 0 else 1
    n_cols = max(1, n_cols)
    n_rows = max(1, n_rows)

    cell_w = w / n_cols
    cell_h = h / n_rows

    if _HAS_NUMPY:
        arr = _to_numpy(img).astype(np.float32)
        out = np.zeros_like(arr)
        for row in range(n_rows):
            y0 = int(row * cell_h)
            y1 = int((row + 1) * cell_h) if row < n_rows - 1 else h
            for col in range(n_cols):
                x0 = int(col * cell_w)
                x1 = int((col + 1) * cell_w) if col < n_cols - 1 else w
                patch = arr[y0:y1, x0:x1]
                mean_color = patch.mean(axis=(0, 1))
                out[y0:y1, x0:x1] = mean_color
        out = np.clip(out, 0, 255).astype(np.uint8)
        return _from_numpy(out, "RGB")
    else:
        # Pure-PIL fallback
        out = Image.new("RGB", (w, h))
        for row in range(n_rows):
            y0 = int(row * cell_h)
            y1 = int((row + 1) * cell_h) if row < n_rows - 1 else h
            for col in range(n_cols):
                x0 = int(col * cell_w)
                x1 = int((col + 1) * cell_w) if col < n_cols - 1 else w
                patch = img.crop((x0, y0, x1, y1))
                # Compute average color via histogram
                stat = ImageStat.Stat(patch)
                mean_color = tuple(int(c) for c in stat.mean[:3])
                out.paste(mean_color, (x0, y0, x1, y1))
        return out


def cartoon_effect(img: Image.Image, blur_radius: int = 5, edge_threshold: int = 100) -> Image.Image:
    """Apply a cartoon-like effect to an image.

    Steps:
        1. Median filter for noise removal.
        2. Bilateral-like smoothing for flat color regions.
        3. Edge detection with simple gradient.
        4. Edge enhancement overlay.

    Args:
        img: Input PIL image.
        blur_radius: Radius for the smoothing step.
        edge_threshold: Threshold for edge detection (0-255).

    Returns:
        Cartoon-styled PIL image in RGB mode.
    """
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Step 1: median filter denoise
    denoised = img.filter(ImageFilter.MedianFilter(size=3))

    # Step 2: bilateral-like smoothing
    smoothed = _blur_with_edge_preserve(denoised, radius=blur_radius)

    # Step 3: edge detection
    gray = smoothed.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    edges = edges.point(lambda p: 255 if p > edge_threshold else 0)

    # Step 4: edge overlay (darken edges)
    if _HAS_NUMPY:
        smooth_arr = _to_numpy(smoothed).astype(np.float32)
        edge_arr = _to_numpy(edges.convert("L")) / 255.0
        edge_arr = edge_arr[:, :, np.newaxis]
        # Darken edge pixels
        darkened = smooth_arr * (1 - edge_arr * 0.7)
        darkened = np.clip(darkened, 0, 255).astype(np.uint8)
        result = _from_numpy(darkened, "RGB")
    else:
        # PIL fallback: use edges as mask to blend with black
        black = Image.new("RGB", img.size, (0, 0, 0))
        result = Image.composite(black, smoothed, edges.convert("L"))

    return result.convert("RGB")


def _estimate_complexity(img: Image.Image) -> str:
    """Lightweight heuristic to estimate image complexity for adaptive simplification.

    Returns one of: ``"photo"``, ``"complex"``, ``"sketch"``.
    """
    rgb = img.convert("RGB")
    w, h = rgb.size
    if w < 8 or h < 8:
        return "sketch"

    # Color complexity via quantization
    small = rgb.resize((max(1, w // 4), max(1, h // 4)), Image.Resampling.NEAREST)
    quantized = small.quantize(colors=16, method=Image.Quantize.MEDIANCUT)
    palette = quantized.getpalette()
    color_count = len(palette) // 3 if palette else 16

    # Edge density
    gray = rgb.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    if _HAS_NUMPY:
        edge_arr = _to_numpy(edges)
        edge_density = float(np.mean(edge_arr)) / 255.0
    else:
        pixels = list(edges.getdata())
        edge_density = sum(pixels) / (255.0 * len(pixels))

    # Sketch: very few colors, high edge density
    if color_count <= 4 and edge_density > 0.25:
        return "sketch"

    # Complex: many colors, moderate edges
    if color_count > 10 and edge_density > 0.1:
        return "complex"

    # Default to photo
    return "photo"


def adaptive_simplify(img: Image.Image, image_type: str = "auto") -> Image.Image:
    """Adaptively simplify an image based on its estimated type.

    Args:
        img: Input PIL image.
        image_type: One of ``"photo"``, ``"complex"``, ``"sketch"``, or ``"auto"``.
            When ``"auto"``, a lightweight heuristic selects the strategy.

    Returns:
        Simplified PIL image in RGB mode.
    """
    image_type = image_type.strip().lower()

    if image_type == "auto":
        image_type = _estimate_complexity(img)

    if image_type == "photo":
        # Semantic simplify + very light cartoon edge overlay
        simplified = semantic_simplify(img, color_clusters=8, edge_preserve=True)
        # Very light edge enhancement
        edges = _edge_mask(simplified, threshold=80)
        if _HAS_NUMPY:
            arr = _to_numpy(simplified).astype(np.float32)
            e_arr = _to_numpy(edges.convert("L")) / 255.0
            e_arr = e_arr[:, :, np.newaxis]
            darkened = arr * (1 - e_arr * 0.3)
            darkened = np.clip(darkened, 0, 255).astype(np.uint8)
            return _from_numpy(darkened, "RGB")
        else:
            black = Image.new("RGB", img.size, (0, 0, 0))
            return Image.composite(black, simplified, edges.convert("L")).convert("RGB")
    elif image_type == "complex":
        return superpixel_simplify(img, n_segments=100)
    elif image_type == "sketch":
        # Strong edge preserve + aggressive quantization
        return semantic_simplify(img, color_clusters=3, edge_preserve=True)
    else:
        # Unknown type: safe default
        return semantic_simplify(img, color_clusters=8, edge_preserve=False)
