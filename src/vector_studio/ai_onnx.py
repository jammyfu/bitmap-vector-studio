from __future__ import annotations

import logging
import urllib.request
from pathlib import Path
from typing import Any

from PIL import Image, ImageFilter, ImageOps

logger = logging.getLogger(__name__)

# ONNX Runtime is an optional dependency.
try:
    import onnxruntime as ort

    _ONNX_AVAILABLE = True
except Exception:  # pragma: no cover
    ort = None  # type: ignore[assignment]
    _ONNX_AVAILABLE = False


# ---------------------------------------------------------------------------
# Model metadata
# ---------------------------------------------------------------------------

MODEL_REGISTRY: dict[str, dict[str, Any]] = {
    "unet-lite": {
        "url": "https://github.com/onnx/models/raw/main/vision/segmentation/unet/model/unet-lite.onnx",
        "description": "Lightweight UNet for foreground/background segmentation.",
        "size_mb": 12,
    },
    "esrgan-lite": {
        "url": "https://github.com/onnx/models/raw/main/vision/super_resolution/esrgan/model/esrgan-lite.onnx",
        "description": "Lightweight ESRGAN for 2x/4x super-resolution.",
        "size_mb": 25,
    },
    "style-sketch": {
        "url": "https://github.com/onnx/models/raw/main/vision/style_transfer/fast_neural_style/model/sketch.onnx",
        "description": "Fast neural style transfer – sketch style.",
        "size_mb": 8,
    },
    "style-oil": {
        "url": "https://github.com/onnx/models/raw/main/vision/style_transfer/fast_neural_style/model/oil.onnx",
        "description": "Fast neural style transfer – oil painting style.",
        "size_mb": 8,
    },
    "style-watercolor": {
        "url": "https://github.com/onnx/models/raw/main/vision/style_transfer/fast_neural_style/model/watercolor.onnx",
        "description": "Fast neural style transfer – watercolor style.",
        "size_mb": 8,
    },
    "style-cartoon": {
        "url": "https://github.com/onnx/models/raw/main/vision/style_transfer/fast_neural_style/model/cartoon.onnx",
        "description": "Fast neural style transfer – cartoon style.",
        "size_mb": 8,
    },
}


# ---------------------------------------------------------------------------
# ONNXModelManager
# ---------------------------------------------------------------------------

class ONNXModelManager:
    """Manages local ONNX model files: listing, downloading, and loading."""

    def __init__(self, models_dir: Path | None = None) -> None:
        """Initialize the manager with a models directory.

        Parameters
        ----------
        models_dir:
            Directory where ``.onnx`` files are stored.  Defaults to
            ``~/.bitmap_vector_studio/models/``.
        """
        if models_dir is None:
            models_dir = Path.home() / ".bitmap_vector_studio" / "models"
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def list_available_models(self) -> list[dict[str, Any]]:
        """List models that are already present on disk.

        Returns
        -------
        list[dict]
            Each dict contains ``name``, ``path``, ``description``, and
            ``size_mb``.
        """
        results: list[dict[str, Any]] = []
        for name, meta in MODEL_REGISTRY.items():
            path = self._model_path(name)
            if path.exists():
                results.append({
                    "name": name,
                    "path": str(path),
                    "description": meta["description"],
                    "size_mb": meta["size_mb"],
                })
        return results

    def is_model_available(self, model_name: str) -> bool:
        """Check whether a registered model has been downloaded.

        Parameters
        ----------
        model_name:
            Key in :data:`MODEL_REGISTRY`.

        Returns
        -------
        bool
        """
        return self._model_path(model_name).exists()

    def download_model(self, model_name: str, url: str | None = None) -> Path:
        """Download a model from *url* (or the registry default) to disk.

        Parameters
        ----------
        model_name:
            Key in :data:`MODEL_REGISTRY`.
        url:
            Optional override URL.  When ``None`` the registry URL is used.

        Returns
        -------
        Path
            Local path of the downloaded ``.onnx`` file.

        Raises
        ------
        ValueError
            If *model_name* is unknown and no *url* is provided.
        RuntimeError
            If the download fails.
        """
        if url is None:
            meta = MODEL_REGISTRY.get(model_name)
            if meta is None:
                valid = ", ".join(sorted(MODEL_REGISTRY))
                raise ValueError(
                    f"Unknown model '{model_name}'. Available: {valid}."
                )
            url = meta["url"]

        dest = self._model_path(model_name)
        logger.info("Downloading %s → %s", url, dest)
        try:
            urllib.request.urlretrieve(url, str(dest))
        except Exception as exc:
            raise RuntimeError(
                f"Failed to download model '{model_name}' from {url}: {exc}"
            ) from exc
        return dest

    def load_model(self, model_path: Path) -> "ort.InferenceSession":
        """Load an ONNX model into an :class:`onnxruntime.InferenceSession`.

        Parameters
        ----------
        model_path:
            Path to a ``.onnx`` file.

        Returns
        -------
        onnxruntime.InferenceSession

        Raises
        ------
        RuntimeError
            If ONNX Runtime is not installed or the file cannot be loaded.
        """
        if not _ONNX_AVAILABLE or ort is None:
            raise RuntimeError(
                "ONNX Runtime is not installed. "
                "Install it with: pip install onnxruntime"
            )
        try:
            return ort.InferenceSession(str(model_path))
        except Exception as exc:
            raise RuntimeError(f"Failed to load ONNX model {model_path}: {exc}") from exc

    def _model_path(self, model_name: str) -> Path:
        """Return the canonical on-disk path for a model name."""
        return self.models_dir / f"{model_name}.onnx"


# ---------------------------------------------------------------------------
# ImageSegmenter
# ---------------------------------------------------------------------------

class ImageSegmenter:
    """Segment images using a lightweight UNet ONNX model."""

    def __init__(self, model_manager: ONNXModelManager | None = None) -> None:
        """Initialize with an optional :class:`ONNXModelManager`."""
        self.model_manager = model_manager or ONNXModelManager()
        self._session: "ort.InferenceSession | None" = None

    def segment(self, image: Image.Image, model_name: str = "unet-lite") -> Image.Image:
        """Run segmentation and return a binary mask.

        When the ONNX model is unavailable the method falls back to a simple
        brightness-based threshold mask so the pipeline never breaks.

        Parameters
        ----------
        image:
            Input PIL image.
        model_name:
            Model to use (default ``"unet-lite"``).

        Returns
        -------
        Image.Image
            Grayscale mask where white (255) = foreground.
        """
        if not self.model_manager.is_model_available(model_name):
            logger.warning(
                "Segmentation model '%s' not found. "
                "Run 'vector-studio ai download %s' to download it. "
                "Falling back to brightness threshold.",
                model_name,
                model_name,
            )
            return self._fallback_mask(image)

        if not _ONNX_AVAILABLE:
            logger.warning("ONNX Runtime not installed; falling back to threshold mask.")
            return self._fallback_mask(image)

        try:
            return self._onnx_segment(image, model_name)
        except Exception as exc:  # noqa: BLE001
            logger.warning("ONNX segmentation failed: %s. Falling back.", exc)
            return self._fallback_mask(image)

    def segment_and_simplify(self, image: Image.Image) -> Image.Image:
        """Segment foreground/background and return a cleaned foreground image.

        The returned image has an alpha channel where the background is
        transparent.

        Parameters
        ----------
        image:
            Input PIL image.

        Returns
        -------
        Image.Image
            RGBA image with background removed.
        """
        mask = self.segment(image)
        # Ensure RGBA
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        # Apply mask as alpha
        r, g, b, a = image.split()
        # Combine existing alpha with mask
        combined_alpha = ImageChops.multiply(a, mask)
        image.putalpha(combined_alpha)
        return image

    def _onnx_segment(self, image: Image.Image, model_name: str) -> Image.Image:
        """Internal ONNX-based segmentation."""
        if self._session is None:
            path = self.model_manager._model_path(model_name)
            self._session = self.model_manager.load_model(path)

        # Pre-process: resize to 256x256, normalize to [0, 1]
        input_size = (256, 256)
        resized = image.convert("RGB").resize(input_size, Image.Resampling.LANCZOS)
        arr = np.array(resized, dtype=np.float32) / 255.0
        arr = np.transpose(arr, (2, 0, 1))  # CHW
        arr = np.expand_dims(arr, axis=0)  # NCHW

        session = self._session
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: arr})
        mask_arr = outputs[0]

        # Post-process: squeeze, threshold, resize back
        mask_arr = np.squeeze(mask_arr)
        if mask_arr.ndim > 2:
            mask_arr = mask_arr[0]
        mask_img = Image.fromarray((mask_arr > 0.5).astype(np.uint8) * 255)
        mask_img = mask_img.resize(image.size, Image.Resampling.NEAREST)
        return mask_img.convert("L")

    @staticmethod
    def _fallback_mask(image: Image.Image) -> Image.Image:
        """Simple brightness threshold mask when ONNX is unavailable."""
        gray = ImageOps.grayscale(image)
        # Threshold: keep brighter pixels as foreground
        return gray.point(lambda p: 255 if p > 128 else 0)


# ---------------------------------------------------------------------------
# StyleTransfer
# ---------------------------------------------------------------------------

class StyleTransfer:
    """Apply artistic style transfer using ONNX models."""

    _STYLE_MAP: dict[str, str] = {
        "sketch": "style-sketch",
        "oil": "style-oil",
        "watercolor": "style-watercolor",
        "cartoon": "style-cartoon",
    }

    def __init__(self, model_manager: ONNXModelManager | None = None) -> None:
        """Initialize with an optional :class:`ONNXModelManager`."""
        self.model_manager = model_manager or ONNXModelManager()
        self._sessions: dict[str, "ort.InferenceSession | None"] = {}

    def transfer(self, image: Image.Image, style: str = "sketch") -> Image.Image:
        """Apply a style transfer to *image*.

        Falls back to PIL filters when the ONNX model is missing or ONNX
        Runtime is not installed.

        Parameters
        ----------
        image:
            Input PIL image.
        style:
            One of ``"sketch"``, ``"oil"``, ``"watercolor"``, ``"cartoon"``.

        Returns
        -------
        Image.Image
            Styled image.
        """
        model_name = self._STYLE_MAP.get(style)
        if model_name is None:
            valid = ", ".join(sorted(self._STYLE_MAP))
            raise ValueError(f"Unknown style '{style}'. Available: {valid}.")

        if not self.model_manager.is_model_available(model_name):
            logger.warning(
                "Style model '%s' not found. "
                "Run 'vector-studio ai download %s' to download it. "
                "Falling back to PIL filters.",
                model_name,
                model_name,
            )
            return self._fallback_style(image, style)

        if not _ONNX_AVAILABLE:
            logger.warning("ONNX Runtime not installed; falling back to PIL filters.")
            return self._fallback_style(image, style)

        try:
            return self._onnx_transfer(image, model_name)
        except Exception as exc:  # noqa: BLE001
            logger.warning("ONNX style transfer failed: %s. Falling back.", exc)
            return self._fallback_style(image, style)

    def preprocess_for_vectorize(self, image: Image.Image) -> Image.Image:
        """Optimise an image for vectorization.

        Steps:
        1. Slight sharpening.
        2. Contrast enhancement.
        3. Optional edge-preserving smoothing.

        Parameters
        ----------
        image:
            Input PIL image.

        Returns
        -------
        Image.Image
            Processed image.
        """
        img = image.convert("RGB")
        # Sharpen
        img = img.filter(ImageFilter.SHARPEN)
        # Auto-contrast
        img = ImageOps.autocontrast(img, cutoff=1)
        # Mild smoothing to reduce noise while keeping edges
        img = img.filter(ImageFilter.MedianFilter(size=3))
        return img

    def _onnx_transfer(self, image: Image.Image, model_name: str) -> Image.Image:
        """Internal ONNX-based style transfer."""
        session = self._sessions.get(model_name)
        if session is None:
            path = self.model_manager._model_path(model_name)
            session = self.model_manager.load_model(path)
            self._sessions[model_name] = session

        input_size = (256, 256)
        resized = image.convert("RGB").resize(input_size, Image.Resampling.LANCZOS)
        arr = np.array(resized, dtype=np.float32) / 255.0
        arr = np.transpose(arr, (2, 0, 1))
        arr = np.expand_dims(arr, axis=0)

        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: arr})
        out_arr = np.squeeze(outputs[0])
        out_arr = np.transpose(out_arr, (1, 2, 0))
        out_arr = np.clip(out_arr * 255, 0, 255).astype(np.uint8)
        out_img = Image.fromarray(out_arr)
        return out_img.resize(image.size, Image.Resampling.LANCZOS)

    @staticmethod
    def _fallback_style(image: Image.Image, style: str) -> Image.Image:
        """PIL-based style approximation when ONNX is unavailable."""
        img = image.convert("RGB")
        if style == "sketch":
            gray = ImageOps.grayscale(img)
            # Invert + blur + color dodge approximation
            inv = ImageOps.invert(gray)
            blur = inv.filter(ImageFilter.GaussianBlur(radius=2))
            # Simple dodge: divide-like effect via point transform
            sketch = ImageChops.subtract(gray, blur)
            sketch = ImageOps.autocontrast(sketch)
            return sketch.convert("RGB")
        elif style == "oil":
            return img.filter(ImageFilter.ModeFilter(size=7))
        elif style == "watercolor":
            smooth = img.filter(ImageFilter.SMOOTH_MORE)
            return ImageOps.autocontrast(smooth)
        elif style == "cartoon":
            # Quantize to a small palette for posterised look
            quantized = img.quantize(colors=16, method=Image.Quantize.MEDIANCUT)
            return quantized.convert("RGB").filter(ImageFilter.SMOOTH)
        return img


# ---------------------------------------------------------------------------
# SuperResolution
# ---------------------------------------------------------------------------

class SuperResolution:
    """Upscale images using an ESRGAN ONNX model."""

    def __init__(self, model_manager: ONNXModelManager | None = None) -> None:
        """Initialize with an optional :class:`ONNXModelManager`."""
        self.model_manager = model_manager or ONNXModelManager()
        self._session: "ort.InferenceSession | None" = None

    def upscale(self, image: Image.Image, scale: int = 2) -> Image.Image:
        """Upscale *image* by *scale* using ESRGAN.

        Falls back to Lanczos resizing when the model is unavailable.

        Parameters
        ----------
        image:
            Input PIL image.
        scale:
            Upscaling factor (default ``2``).

        Returns
        -------
        Image.Image
            Upscaled image.
        """
        model_name = "esrgan-lite"
        if not self.model_manager.is_model_available(model_name):
            logger.warning(
                "Super-resolution model '%s' not found. "
                "Run 'vector-studio ai download %s' to download it. "
                "Falling back to Lanczos resize.",
                model_name,
                model_name,
            )
            return self._fallback_upscale(image, scale)

        if not _ONNX_AVAILABLE:
            logger.warning("ONNX Runtime not installed; falling back to Lanczos resize.")
            return self._fallback_upscale(image, scale)

        try:
            return self._onnx_upscale(image, scale)
        except Exception as exc:  # noqa: BLE001
            logger.warning("ONNX super-resolution failed: %s. Falling back.", exc)
            return self._fallback_upscale(image, scale)

    def _onnx_upscale(self, image: Image.Image, scale: int) -> Image.Image:
        """Internal ONNX-based upscaling."""
        if self._session is None:
            path = self.model_manager._model_path("esrgan-lite")
            self._session = self.model_manager.load_model(path)

        session = self._session
        input_size = (256, 256)
        resized = image.convert("RGB").resize(input_size, Image.Resampling.LANCZOS)
        arr = np.array(resized, dtype=np.float32) / 255.0
        arr = np.transpose(arr, (2, 0, 1))
        arr = np.expand_dims(arr, axis=0)

        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: arr})
        out_arr = np.squeeze(outputs[0])
        out_arr = np.transpose(out_arr, (1, 2, 0))
        out_arr = np.clip(out_arr * 255, 0, 255).astype(np.uint8)
        out_img = Image.fromarray(out_arr)

        target_size = (image.width * scale, image.height * scale)
        return out_img.resize(target_size, Image.Resampling.LANCZOS)

    @staticmethod
    def _fallback_upscale(image: Image.Image, scale: int) -> Image.Image:
        """PIL-based Lanczos upscaling fallback."""
        new_size = (image.width * scale, image.height * scale)
        return image.resize(new_size, Image.Resampling.LANCZOS)


# ---------------------------------------------------------------------------
# AIProcessor
# ---------------------------------------------------------------------------

class AIProcessor:
    """Unified entry point for local ONNX-based image processing."""

    def __init__(self, model_manager: ONNXModelManager | None = None) -> None:
        """Initialize sub-processors with an optional shared manager."""
        self.segmenter = ImageSegmenter(model_manager)
        self.style_transfer = StyleTransfer(model_manager)
        self.super_res = SuperResolution(model_manager)

    def process(self, image: Image.Image, task: str, **kwargs: Any) -> Image.Image:
        """Run an AI processing *task* on *image*.

        Parameters
        ----------
        image:
            Input PIL image.
        task:
            One of ``"segment"``, ``"style_transfer"``, ``"upscale"``,
            ``"auto_enhance"``.
        **kwargs:
            Task-specific options forwarded to the underlying processor.

        Returns
        -------
        Image.Image
            Processed image.

        Raises
        ------
        ValueError
            If *task* is unknown.
        """
        if task == "segment":
            model_name = kwargs.get("model_name", "unet-lite")
            return self.segmenter.segment(image, model_name=model_name)
        elif task == "style_transfer":
            style = kwargs.get("style", "sketch")
            return self.style_transfer.transfer(image, style=style)
        elif task == "upscale":
            scale = kwargs.get("scale", 2)
            return self.super_res.upscale(image, scale=scale)
        elif task == "auto_enhance":
            return self._auto_enhance(image, **kwargs)
        else:
            valid = "segment, style_transfer, upscale, auto_enhance"
            raise ValueError(f"Unknown task '{task}'. Available: {valid}.")

    def _auto_enhance(self, image: Image.Image, **kwargs: Any) -> Image.Image:
        """Chain upscale → style preprocess for best vectorization results.

        Parameters
        ----------
        image:
            Input PIL image.
        **kwargs:
            ``scale`` (int) and ``style`` (str) are supported.

        Returns
        -------
        Image.Image
            Enhanced image.
        """
        scale = kwargs.get("scale", 2)
        img = self.super_res.upscale(image, scale=scale)
        img = self.style_transfer.preprocess_for_vectorize(img)
        return img


# ---------------------------------------------------------------------------
# Delayed import of numpy so the module can be imported without it.
# ---------------------------------------------------------------------------

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None  # type: ignore[assignment]

# ImageChops is used by the fallback paths; import here to keep the file self-contained.
from PIL import ImageChops
