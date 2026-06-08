from __future__ import annotations

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
    return Image.fromarray(arr.astype(np.uint8))


# ---------------------------------------------------------------------------
# Convolution helpers (NumPy-based, no OpenCV)
# ---------------------------------------------------------------------------

def _apply_kernel(img: Image.Image, kernel: Any) -> Image.Image:
    """Apply a 2D convolution kernel to a grayscale or RGB image using NumPy."""
    if not _HAS_NUMPY:
        # Fallback to PIL's built-in filters when NumPy is missing.
        return img.filter(ImageFilter.Kernel((3, 3), kernel.flatten().tolist(), scale=1))

    arr = _to_numpy(img).astype(np.float32)
    mode = img.mode
    if mode == "RGB":
        out = np.zeros_like(arr)
        for c in range(3):
            out[:, :, c] = _convolve2d(arr[:, :, c], kernel)
        out = np.clip(out, 0, 255).astype(np.uint8)
        return _from_numpy(out, "RGB")
    else:
        gray = arr if arr.ndim == 2 else arr[:, :, 0]
        out = _convolve2d(gray, kernel)
        out = np.clip(out, 0, 255).astype(np.uint8)
        return Image.fromarray(out)


def _convolve2d(arr: Any, kernel: Any) -> Any:
    """Simple 2D convolution with zero padding."""
    kh, kw = kernel.shape
    pad_h, pad_w = kh // 2, kw // 2
    padded = np.pad(arr, ((pad_h, pad_h), (pad_w, pad_w)), mode="edge")
    result = np.zeros_like(arr)
    for i in range(kh):
        for j in range(kw):
            result += kernel[i, j] * padded[i : i + arr.shape[0], j : j + arr.shape[1]]
    return result


# ---------------------------------------------------------------------------
# Public enhancement API
# ---------------------------------------------------------------------------

def edge_enhance(img: Image.Image, strength: float = 1.0) -> Image.Image:
    """Enhance edges using an unsharp-mask style convolution.

    Args:
        img: Input PIL image.
        strength: Enhancement multiplier (0.0 = no effect, 1.0 = moderate).

    Returns:
        Enhanced PIL image.
    """
    if strength <= 0:
        return img.copy()

    # Unsharp mask via PIL is fast and high-quality.
    radius = 2
    percent = int(100 * strength)
    threshold = 3
    return img.filter(ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=threshold))


def scan_denoise(img: Image.Image, strength: int = 2) -> Image.Image:
    """Denoise a scanned document: conservative median filter + slight sharpening.

    Args:
        img: Input PIL image.
        strength: Median filter size (1 = 3x3, 2 = 5x5, 3 = 7x7).

    Returns:
        Denoised PIL image.
    """
    size = 1 + 2 * max(1, min(strength, 5))
    denoised = img.filter(ImageFilter.MedianFilter(size=size))
    # Slight sharpen to restore edge crispness lost to median filter.
    return denoised.filter(ImageFilter.UnsharpMask(radius=1, percent=80, threshold=3))


def auto_contrast(img: Image.Image, cutoff: float = 0.0) -> Image.Image:
    """Stretch image histogram to improve overall contrast.

    Args:
        img: Input PIL image.
        cutoff: Percentage of light/dark pixels to ignore at the extremes
            (0.0 = full stretch, 1.0 = most conservative).

    Returns:
        Contrast-stretched PIL image.
    """
    cutoff = max(0.0, min(cutoff, 50.0))
    return ImageOps.autocontrast(img, cutoff=int(cutoff))


def sharpen(
    img: Image.Image,
    radius: int = 2,
    percent: int = 150,
    threshold: int = 3,
) -> Image.Image:
    """Sharpen an image using Pillow's UnsharpMask filter.

    Args:
        img: Input PIL image.
        radius: Gaussian blur radius used for the mask.
        percent: Strength of the sharpening effect.
        threshold: Minimum brightness difference required to apply sharpening.

    Returns:
        Sharpened PIL image.
    """
    return img.filter(ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=threshold))


def adaptive_enhance(img: Image.Image, image_type: str = "auto") -> Image.Image:
    """Apply enhancement tailored to the image category.

    Args:
        img: Input PIL image.
        image_type: One of ``"scan"``, ``"photo"``, ``"logo"``, or ``"auto"``.
            When ``"auto"``, a lightweight heuristic is used to pick the strategy.

    Returns:
        Enhanced PIL image.
    """
    image_type = image_type.strip().lower()

    if image_type == "auto":
        image_type = _guess_image_type(img)

    if image_type == "scan":
        return scan_denoise(img, strength=2)
    elif image_type == "photo":
        return sharpen(img, radius=1, percent=80, threshold=3)
    elif image_type == "logo":
        return edge_enhance(img, strength=1.2)
    else:
        # Unknown type: safe default.
        return auto_contrast(img, cutoff=0.0)


def _guess_image_type(img: Image.Image) -> str:
    """Lightweight heuristic to guess whether an image is a scan, photo, or logo."""
    rgb = img.convert("RGB")
    w, h = rgb.size
    if w < 8 or h < 8:
        return "photo"

    # Quantize to estimate color complexity.
    small = rgb.resize((max(1, w // 4), max(1, h // 4)), Image.Resampling.NEAREST)
    quantized = small.quantize(colors=16, method=Image.Quantize.MEDIANCUT)
    palette = quantized.getpalette()
    color_count = len(palette) // 3 if palette else 16

    # Edge density via simple difference filter.
    gray = rgb.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    if _HAS_NUMPY:
        edge_arr = _to_numpy(edges)
        edge_density = float(np.mean(edge_arr)) / 255.0
    else:
        # Slow fallback.
        pixels = list(edges.getdata())
        edge_density = sum(pixels) / (255.0 * len(pixels))

    # Scans: lots of high-contrast edges, few colors, usually large.
    if edge_density > 0.15 and color_count < 6 and max(w, h) > 800:
        return "scan"

    # Logos: few colors, very sharp edges.
    if color_count < 8 and edge_density > 0.2:
        return "logo"

    # Default to photo for everything else.
    return "photo"
