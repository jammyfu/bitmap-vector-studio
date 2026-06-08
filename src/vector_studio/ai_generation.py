from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageFilter, ImageOps, ImageChops

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_STYLE_PALETTES: dict[str, list[tuple[int, int, int]]] = {
    "flat": [
        (255, 99, 71),   # tomato
        (60, 179, 113),  # medium sea green
        (30, 144, 255),  # dodger blue
        (255, 215, 0),   # gold
        (238, 130, 238), # violet
    ],
    "line": [
        (0, 0, 0),
        (64, 64, 64),
        (128, 128, 128),
        (192, 192, 192),
        (255, 255, 255),
    ],
    "gradient": [
        (25, 25, 112),   # midnight blue
        (70, 130, 180),  # steel blue
        (135, 206, 250), # light sky blue
        (255, 255, 224), # light yellow
        (255, 165, 0),   # orange
    ],
    "3d": [
        (139, 69, 19),   # saddle brown
        (205, 133, 63),  # peru
        (222, 184, 135), # burlywood
        (245, 222, 179), # wheat
        (255, 250, 240), # floral white
    ],
    "sketch": [
        (40, 40, 40),
        (80, 80, 80),
        (120, 120, 120),
        (160, 160, 160),
        (200, 200, 200),
    ],
    "minimal": [
        (0, 0, 0),
        (255, 255, 255),
        (200, 200, 200),
    ],
    "modern": [
        (0, 0, 0),
        (255, 255, 255),
        (0, 123, 255),
        (40, 167, 69),
        (220, 53, 69),
    ],
    "cartoon": [
        (255, 0, 0),
        (0, 255, 0),
        (0, 0, 255),
        (255, 255, 0),
        (255, 0, 255),
        (0, 255, 255),
    ],
    "watercolor": [
        (176, 224, 230), # powder blue
        (255, 228, 196), # bisque
        (221, 160, 221), # plum
        (152, 251, 152), # pale green
        (255, 182, 193), # light pink
    ],
}

_ICON_SIZE = 256
_LOGO_SIZE = (512, 256)
_ILLUSTRATION_SIZE = (512, 512)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _prompt_seed(prompt: str) -> int:
    """Deterministic integer seed from *prompt*."""
    return int(hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8], 16)


def _rng_from_prompt(prompt: str) -> np.random.Generator:
    """Create a NumPy RNG seeded from *prompt*."""
    return np.random.default_rng(_prompt_seed(prompt))


def _quantize_to_palette(image: Image.Image, palette: list[tuple[int, int, int]]) -> Image.Image:
    """Reduce an image to the nearest colors in *palette*."""
    arr = np.array(image.convert("RGB"), dtype=np.float32)
    palette_arr = np.array(palette, dtype=np.float32)
    # Compute distance to each palette color
    distances = np.linalg.norm(arr[:, :, np.newaxis, :] - palette_arr[np.newaxis, np.newaxis, :, :], axis=3)
    nearest = np.argmin(distances, axis=2)
    quantized = palette_arr[nearest].astype(np.uint8)
    return Image.fromarray(quantized)


def _color_transfer(source: Image.Image, target: Image.Image) -> Image.Image:
    """Transfer the mean/std of *source* colors to *target*."""
    src_arr = np.array(source.convert("RGB"), dtype=np.float32)
    tgt_arr = np.array(target.convert("RGB"), dtype=np.float32)

    for c in range(3):
        src_mean, src_std = src_arr[:, :, c].mean(), src_arr[:, :, c].std() + 1e-6
        tgt_mean, tgt_std = tgt_arr[:, :, c].mean(), tgt_arr[:, :, c].std() + 1e-6
        tgt_arr[:, :, c] = (tgt_arr[:, :, c] - tgt_mean) * (src_std / tgt_std) + src_mean

    tgt_arr = np.clip(tgt_arr, 0, 255).astype(np.uint8)
    return Image.fromarray(tgt_arr)


# ---------------------------------------------------------------------------
# VectorDiffusion
# ---------------------------------------------------------------------------

class VectorDiffusion:
    """Simplified diffusion process using only Pillow and NumPy.

    This is a **simulated** diffusion pipeline: it does not run a real
    neural network, but it produces deterministic, aesthetically varied
    images from a text prompt by iteratively denoising a random field
    toward a prompt-derived color palette.
    """

    def __init__(self, models_dir: Path | None = None) -> None:
        """Initialize the diffusion simulator.

        Parameters
        ----------
        models_dir:
            Ignored – kept for API compatibility with other AI modules.
        """
        self.models_dir = models_dir

    def diffuse(self, prompt: str, steps: int = 20, size: tuple[int, int] = (512, 512)) -> Image.Image:
        """Generate an image from *prompt* via simulated diffusion.

        The process:
        1. Hash the prompt to seed a RNG.
        2. Create a random noise field.
        3. Iteratively smooth and nudge the field toward a palette derived
           from the prompt.
        4. Return the resulting RGB image.

        Parameters
        ----------
        prompt:
            Text description that guides color and structure.
        steps:
            Number of denoising iterations (default 20).
        size:
            Output ``(width, height)``.

        Returns
        -------
        Image.Image
            Generated RGB image.
        """
        rng = _rng_from_prompt(prompt)
        width, height = size

        # Start from random noise
        field = rng.random((height, width, 3), dtype=np.float32)

        # Derive a palette from the prompt
        palette = self._palette_from_prompt(prompt, rng)
        palette_norm = np.array(palette, dtype=np.float32) / 255.0

        # Iterative denoising / guidance
        for step in range(steps):
            # Slight Gaussian-like smoothing via simple box blur
            field = self._smooth_field(field)
            # Pull colors toward palette based on step progress
            alpha = (step + 1) / steps
            field = self._guide_to_palette(field, palette_norm, strength=alpha * 0.3)
            # Add tiny noise to keep texture
            noise = rng.normal(0, 0.02 * (1 - alpha), field.shape)
            field = np.clip(field + noise, 0.0, 1.0)

        # Final quantization to palette for a clean vector-friendly look
        arr = (field * 255).astype(np.uint8)
        img = Image.fromarray(arr)
        img = _quantize_to_palette(img, palette)
        return img

    @staticmethod
    def _palette_from_prompt(prompt: str, rng: np.random.Generator) -> list[tuple[int, int, int]]:
        """Build a deterministic but varied palette from *prompt*."""
        base = _STYLE_PALETTES.get("flat", _STYLE_PALETTES["flat"])
        # Shuffle based on prompt-derived RNG
        indices = rng.choice(len(base), size=min(5, len(base)), replace=False)
        palette = [base[i] for i in indices]
        # Slightly perturb colors
        perturbed: list[tuple[int, int, int]] = []
        for r, g, b in palette:
            dr, dg, db = rng.integers(-20, 21, size=3)
            perturbed.append((
                int(np.clip(r + dr, 0, 255)),
                int(np.clip(g + dg, 0, 255)),
                int(np.clip(b + db, 0, 255)),
            ))
        return perturbed

    @staticmethod
    def _smooth_field(field: np.ndarray) -> np.ndarray:
        """Apply a lightweight 3x3 average smooth using pure NumPy."""
        kernel = np.ones((3, 3), dtype=np.float32) / 9.0
        smoothed = np.empty_like(field)
        for c in range(field.shape[2]):
            channel = field[:, :, c]
            # Pad with edge values
            padded = np.pad(channel, pad_width=1, mode="edge")
            # Simple 2D convolution via slicing
            conv = (
                padded[0:-2, 0:-2] + padded[0:-2, 1:-1] + padded[0:-2, 2:] +
                padded[1:-1, 0:-2] + padded[1:-1, 1:-1] + padded[1:-1, 2:] +
                padded[2:, 0:-2] + padded[2:, 1:-1] + padded[2:, 2:]
            ) / 9.0
            smoothed[:, :, c] = conv
        return smoothed

    @staticmethod
    def _guide_to_palette(field: np.ndarray, palette: np.ndarray, strength: float) -> np.ndarray:
        """Nudge each pixel toward its nearest palette color."""
        # field: HxWx3, palette: Nx3
        distances = np.linalg.norm(field[:, :, np.newaxis, :] - palette[np.newaxis, np.newaxis, :, :], axis=3)
        nearest = palette[np.argmin(distances, axis=2)]
        return field * (1 - strength) + nearest * strength


# ---------------------------------------------------------------------------
# StyleEncoder
# ---------------------------------------------------------------------------

class StyleEncoder:
    """Extract and apply style feature vectors using purely NumPy/Pillow."""

    def encode_style(self, image: Image.Image) -> list[float]:
        """Extract a style feature vector from *image*.

        The vector contains:
        - Mean RGB (3)
        - Std RGB (3)
        - Dominant hue bins (4)
        - Brightness mean/std (2)
        - Saturation mean/std (2)

        Total length: 14 dimensions.

        Parameters
        ----------
        image:
            Input PIL image.

        Returns
        -------
        list[float]
            14-dimensional style vector.
        """
        img = image.convert("RGB")
        arr = np.array(img, dtype=np.float32) / 255.0

        # RGB stats
        mean_rgb = arr.mean(axis=(0, 1))
        std_rgb = arr.std(axis=(0, 1))

        # HSV-ish approximations for hue / saturation / brightness
        max_c = arr.max(axis=2)
        min_c = arr.min(axis=2)
        delta = max_c - min_c + 1e-6
        brightness = max_c
        saturation = delta / (max_c + 1e-6)

        # Simple hue approximation
        hue = np.zeros_like(max_c)
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        mask = delta > 1e-3
        # Red is max
        mask_r = mask & (max_c == r)
        hue[mask_r] = ((g[mask_r] - b[mask_r]) / delta[mask_r]) % 6
        # Green is max
        mask_g = mask & (max_c == g)
        hue[mask_g] = ((b[mask_g] - r[mask_g]) / delta[mask_g]) + 2
        # Blue is max
        mask_b = mask & (max_c == b)
        hue[mask_b] = ((r[mask_b] - g[mask_b]) / delta[mask_b]) + 4
        hue = hue / 6.0  # normalize 0-1

        # Hue histogram (4 bins)
        hue_hist, _ = np.histogram(hue[mask], bins=4, range=(0, 1))
        hue_hist = hue_hist / (hue_hist.sum() + 1e-6)

        vector = [
            *mean_rgb.tolist(),
            *std_rgb.tolist(),
            *hue_hist.tolist(),
            float(brightness.mean()),
            float(brightness.std()),
            float(saturation.mean()),
            float(saturation.std()),
        ]
        return [float(v) for v in vector]

    def apply_style(self, target: Image.Image, style_vector: list[float]) -> Image.Image:
        """Apply a encoded style to *target*.

        Uses the mean/std from the style vector to perform a color transfer
        and adjusts saturation/brightness to match the style.

        Parameters
        ----------
        target:
            Image to restyle.
        style_vector:
            14-dimensional vector from :meth:`encode_style`.

        Returns
        -------
        Image.Image
            Restyled image.
        """
        if len(style_vector) < 6:
            raise ValueError("style_vector must have at least 6 elements (mean_rgb + std_rgb)")

        target = target.convert("RGB")
        tgt_arr = np.array(target, dtype=np.float32) / 255.0

        style_mean = np.array(style_vector[:3])
        style_std = np.array(style_vector[3:6])
        tgt_mean = tgt_arr.mean(axis=(0, 1))
        tgt_std = tgt_arr.std(axis=(0, 1)) + 1e-6

        # Match mean and std
        matched = (tgt_arr - tgt_mean) * (style_std / tgt_std) + style_mean
        matched = np.clip(matched, 0, 1)

        # Adjust brightness / saturation if vector is long enough
        if len(style_vector) >= 14:
            target_brightness_mean = matched.max(axis=2).mean()
            style_brightness_mean = style_vector[10]
            brightness_shift = style_brightness_mean - target_brightness_mean
            matched = np.clip(matched + brightness_shift, 0, 1)

        out_arr = (matched * 255).astype(np.uint8)
        return Image.fromarray(out_arr)


# ---------------------------------------------------------------------------
# VectorGenerator
# ---------------------------------------------------------------------------

class VectorGenerator:
    """AI generative vector-style image creation without PyTorch/TensorFlow.

    Uses :class:`VectorDiffusion` for the core image synthesis and applies
    style-specific post-processing to produce flat, line-art, gradient,
    3-D, or sketch aesthetics suitable for vectorization.
    """

    def __init__(self, models_dir: Path | None = None) -> None:
        """Initialize the generator.

        Parameters
        ----------
        models_dir:
            Optional directory for future model storage. Currently unused.
        """
        self.models_dir = models_dir
        self.diffusion = VectorDiffusion(models_dir)
        self.style_encoder = StyleEncoder()

    def generate_from_text(
        self,
        prompt: str,
        style: str = "flat",
        size: tuple[int, int] = (512, 512),
    ) -> Image.Image:
        """Generate a vector-style image from a text prompt.

        Parameters
        ----------
        prompt:
            Text description of the desired image.
        style:
            One of ``"flat"``, ``"line"``, ``"gradient"``, ``"3d"``,
            ``"sketch"``.
        size:
            Output ``(width, height)``.

        Returns
        -------
        Image.Image
            Generated RGB image.

        Raises
        ------
        ValueError
            If *style* is not supported.
        """
        valid = {"flat", "line", "gradient", "3d", "sketch"}
        if style not in valid:
            raise ValueError(f"Unknown style '{style}'. Available: {', '.join(sorted(valid))}.")

        base = self.diffusion.diffuse(prompt, steps=20, size=size)
        return self._apply_style_postprocess(base, style)

    def generate_from_image(
        self,
        image: Image.Image,
        prompt: str | None = None,
    ) -> Image.Image:
        """Image-to-image generation: restyle a reference image.

        The reference image provides structural guidance; an optional
        *prompt* can shift the color palette.

        Parameters
        ----------
        image:
            Reference image.
        prompt:
            Optional text prompt to guide color/style.

        Returns
        -------
        Image.Image
            Generated RGB image.
        """
        # Encode the reference image's style
        style_vec = self.style_encoder.encode_style(image)

        # Generate a new image from prompt (or generic if no prompt)
        gen_prompt = prompt or "vector art inspired by reference"
        base = self.diffusion.diffuse(gen_prompt, steps=20, size=image.size)

        # Apply the reference style
        styled = self.style_encoder.apply_style(base, style_vec)

        # Blend with original structure to preserve composition
        blended = ImageChops.blend(image.convert("RGB"), styled, alpha=0.5)
        return blended

    def generate_icon(self, prompt: str, style: str = "flat") -> Image.Image:
        """Generate a square icon image.

        Parameters
        ----------
        prompt:
            Text description of the icon.
        style:
            One of ``"flat"``, ``"minimal"``, ``"line"``, ``"gradient"``.

        Returns
        -------
        Image.Image
            Generated RGB icon (256x256).
        """
        valid = {"flat", "minimal", "line", "gradient"}
        if style not in valid:
            raise ValueError(f"Unknown icon style '{style}'. Available: {', '.join(sorted(valid))}.")

        base = self.diffusion.diffuse(prompt, steps=16, size=(_ICON_SIZE, _ICON_SIZE))
        processed = self._apply_style_postprocess(base, style)

        # Center-crop to square if somehow not square
        if processed.size[0] != processed.size[1]:
            min_side = min(processed.size)
            processed = processed.crop((
                (processed.width - min_side) // 2,
                (processed.height - min_side) // 2,
                (processed.width + min_side) // 2,
                (processed.height + min_side) // 2,
            ))
        return processed.resize((_ICON_SIZE, _ICON_SIZE), Image.Resampling.LANCZOS)

    def generate_logo(self, prompt: str, style: str = "minimal") -> Image.Image:
        """Generate a logo image.

        Parameters
        ----------
        prompt:
            Text description of the logo.
        style:
            One of ``"minimal"``, ``"modern"``, ``"flat"``.

        Returns
        -------
        Image.Image
            Generated RGB logo (512x256).
        """
        valid = {"minimal", "modern", "flat"}
        if style not in valid:
            raise ValueError(f"Unknown logo style '{style}'. Available: {', '.join(sorted(valid))}.")

        base = self.diffusion.diffuse(prompt, steps=18, size=_LOGO_SIZE)
        processed = self._apply_style_postprocess(base, style)

        # Logos should be clean: high contrast, limited palette
        palette = _STYLE_PALETTES.get(style, _STYLE_PALETTES["minimal"])
        quantized = _quantize_to_palette(processed, palette)
        # Sharpen edges
        sharpened = quantized.filter(ImageFilter.SHARPEN)
        return sharpened

    def generate_illustration(self, prompt: str, style: str = "cartoon") -> Image.Image:
        """Generate an illustration image.

        Parameters
        ----------
        prompt:
            Text description of the illustration.
        style:
            One of ``"cartoon"``, ``"watercolor"``, ``"sketch"``.

        Returns
        -------
        Image.Image
            Generated RGB illustration (512x512).
        """
        valid = {"cartoon", "watercolor", "sketch"}
        if style not in valid:
            raise ValueError(f"Unknown illustration style '{style}'. Available: {', '.join(sorted(valid))}.")

        base = self.diffusion.diffuse(prompt, steps=22, size=_ILLUSTRATION_SIZE)
        processed = self._apply_style_postprocess(base, style)
        return processed

    @staticmethod
    def _apply_style_postprocess(image: Image.Image, style: str) -> Image.Image:
        """Apply style-specific PIL post-processing.

        Parameters
        ----------
        image:
            Base generated image.
        style:
            Style name.

        Returns
        -------
        Image.Image
            Post-processed image.
        """
        img = image.convert("RGB")

        if style == "flat":
            palette = _STYLE_PALETTES.get("flat", _STYLE_PALETTES["flat"])
            img = _quantize_to_palette(img, palette)
            img = img.filter(ImageFilter.SMOOTH_MORE)
        elif style == "line":
            gray = ImageOps.grayscale(img)
            inv = ImageOps.invert(gray)
            blur = inv.filter(ImageFilter.GaussianBlur(radius=2))
            sketch = ImageChops.subtract(gray, blur)
            sketch = ImageOps.autocontrast(sketch)
            img = sketch.convert("RGB")
        elif style == "gradient":
            img = img.filter(ImageFilter.SMOOTH_MORE)
            img = img.filter(ImageFilter.SMOOTH_MORE)
            img = ImageOps.autocontrast(img, cutoff=1)
        elif style == "3d":
            # Fake shading via emboss-like edge detection
            gray = ImageOps.grayscale(img)
            edges = gray.filter(ImageFilter.FIND_EDGES)
            shaded = ImageChops.multiply(gray, edges)
            shaded = ImageOps.autocontrast(shaded)
            img = shaded.convert("RGB")
        elif style == "sketch":
            gray = ImageOps.grayscale(img)
            inv = ImageOps.invert(gray)
            blur = inv.filter(ImageFilter.GaussianBlur(radius=3))
            sketch = ImageChops.subtract(gray, blur)
            sketch = ImageOps.autocontrast(sketch)
            img = sketch.convert("RGB")
        elif style == "minimal":
            palette = _STYLE_PALETTES.get("minimal", _STYLE_PALETTES["minimal"])
            img = _quantize_to_palette(img, palette)
            img = img.filter(ImageFilter.SHARPEN)
        elif style == "modern":
            palette = _STYLE_PALETTES.get("modern", _STYLE_PALETTES["modern"])
            img = _quantize_to_palette(img, palette)
            img = img.filter(ImageFilter.SHARPEN)
        elif style == "cartoon":
            palette = _STYLE_PALETTES.get("cartoon", _STYLE_PALETTES["cartoon"])
            img = _quantize_to_palette(img, palette)
            img = img.filter(ImageFilter.SMOOTH)
        elif style == "watercolor":
            palette = _STYLE_PALETTES.get("watercolor", _STYLE_PALETTES["watercolor"])
            img = _quantize_to_palette(img, palette)
            img = img.filter(ImageFilter.SMOOTH_MORE)
            img = img.filter(ImageFilter.GaussianBlur(radius=1))

        return img


# ---------------------------------------------------------------------------
# Optional: unified entry point (mirrors AIProcessor pattern)
# ---------------------------------------------------------------------------

class AIGenerationProcessor:
    """Unified entry point for generative AI tasks."""

    def __init__(self, models_dir: Path | None = None) -> None:
        """Initialize sub-processors."""
        self.generator = VectorGenerator(models_dir)
        self.style_encoder = StyleEncoder()

    def generate(self, task: str, prompt: str, **kwargs: Any) -> Image.Image:
        """Run a generative *task*.

        Parameters
        ----------
        task:
            One of ``"text"``, ``"icon"``, ``"logo"``, ``"illustration"``.
        prompt:
            Text prompt.
        **kwargs:
            Task-specific options forwarded to the generator.

        Returns
        -------
        Image.Image
            Generated image.

        Raises
        ------
        ValueError
            If *task* is unknown.
        """
        if task == "text":
            return self.generator.generate_from_text(prompt, **kwargs)
        elif task == "icon":
            return self.generator.generate_icon(prompt, **kwargs)
        elif task == "logo":
            return self.generator.generate_logo(prompt, **kwargs)
        elif task == "illustration":
            return self.generator.generate_illustration(prompt, **kwargs)
        else:
            valid = "text, icon, logo, illustration"
            raise ValueError(f"Unknown task '{task}'. Available: {valid}.")
