from __future__ import annotations

import logging
import platform
import sys
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image

logger = logging.getLogger(__name__)


class GPUBackend(Enum):
    """Supported GPU acceleration backends."""

    NONE = "none"
    CUDA = "cuda"
    METAL = "metal"
    OPENCL = "opencl"


def detect_gpu() -> GPUBackend:
    """Detect the best available GPU backend.

    The detection order is:
    1. CUDA (via ``cupy`` or ``pycuda``)
    2. Metal (macOS, via ``metal`` or ``torch`` MPS)
    3. OpenCL (via ``pyopencl``)

    Returns
    -------
    GPUBackend
        The first successfully detected backend, or ``GPUBackend.NONE``.
    """
    # CUDA via cupy
    try:
        import cupy as cp  # type: ignore[import-untyped]

        if cp.cuda.runtime.getDeviceCount() > 0:
            return GPUBackend.CUDA
    except Exception:
        pass

    # CUDA via pycuda
    try:
        import pycuda.driver as cuda  # type: ignore[import-untyped]

        cuda.init()
        if cuda.Device.count() > 0:
            return GPUBackend.CUDA
    except Exception:
        pass

    # Metal (macOS)
    if sys.platform == "darwin":
        try:
            import metal  # type: ignore[import-untyped]

            return GPUBackend.METAL
        except Exception:
            pass
        try:
            import torch  # type: ignore[import-untyped]

            if torch.backends.mps.is_available():
                return GPUBackend.METAL
        except Exception:
            pass

    # OpenCL
    try:
        import pyopencl as cl  # type: ignore[import-untyped]

        platforms = cl.get_platforms()
        if platforms:
            return GPUBackend.OPENCL
    except Exception:
        pass

    return GPUBackend.NONE


def gpu_available() -> bool:
    """Quickly check whether any GPU backend is available.

    Returns
    -------
    bool
        ``True`` if a GPU backend was detected.
    """
    return detect_gpu() != GPUBackend.NONE


def gpu_preprocess(image: "Image.Image", backend: GPUBackend | None = None) -> "Image.Image":
    """Apply GPU-accelerated preprocessing (blur + edge detection) when possible.

    If the requested backend is unavailable or the operation fails, the function
    gracefully falls back to CPU-based Pillow processing.

    Parameters
    ----------
    image:
        Input Pillow image.
    backend:
        Specific backend to use.  If ``None``, ``detect_gpu()`` is called.

    Returns
    -------
    Image.Image
        The preprocessed image (blurred and with edges enhanced).
    """
    from PIL import Image, ImageFilter

    if backend is None:
        backend = detect_gpu()

    if backend == GPUBackend.NONE:
        logger.debug("No GPU backend available; using CPU fallback.")
        return _cpu_preprocess(image)

    try:
        if backend == GPUBackend.CUDA:
            return _cuda_preprocess(image)
        if backend == GPUBackend.OPENCL:
            return _opencl_preprocess(image)
        if backend == GPUBackend.METAL:
            return _metal_preprocess(image)
    except Exception as exc:
        logger.warning("GPU preprocessing failed (%s): %s. Falling back to CPU.", backend.value, exc)

    return _cpu_preprocess(image)


def _cpu_preprocess(image: "Image.Image") -> "Image.Image":
    """CPU fallback: mild Gaussian blur followed by edge enhancement."""
    from PIL import Image, ImageFilter

    blurred = image.filter(ImageFilter.GaussianBlur(radius=1))
    # Simple edge enhancement via FIND_EDGES on a copy, then blend
    edges = image.filter(ImageFilter.FIND_EDGES)
    return Image.blend(blurred, edges, alpha=0.15)


def _cuda_preprocess(image: "Image.Image") -> "Image.Image":
    """CUDA-accelerated blur + edge detection via cupy."""
    try:
        import cupy as cp  # type: ignore[import-untyped]
        import numpy as np
        from PIL import Image

        arr = np.array(image.convert("RGB"))
        # Gaussian blur via separable convolution on GPU
        kernel = cp.array([1, 4, 6, 4, 1], dtype=cp.float32) / 16.0
        gpu_arr = cp.asarray(arr.astype(cp.float32))
        blurred = _separable_convolve_3d(gpu_arr, kernel)
        # Edge detection: Sobel on GPU
        edges = _sobel_gpu(blurred)
        result = cp.asarray(blurred * 0.85 + edges * 0.15).get().clip(0, 255).astype(np.uint8)
        return Image.fromarray(result)
    except Exception as exc:
        logger.debug("CUDA preprocess error: %s", exc)
        raise


def _opencl_preprocess(image: "Image.Image") -> "Image.Image":
    """OpenCL-accelerated blur + edge detection via pyopencl."""
    try:
        import numpy as np
        import pyopencl as cl  # type: ignore[import-untyped]
        from PIL import Image

        arr = np.array(image.convert("RGB")).astype(np.float32)
        ctx = cl.create_some_context()
        queue = cl.CommandQueue(ctx)
        mf = cl.mem_flags
        buf_in = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=arr)
        buf_out = cl.Buffer(ctx, mf.WRITE_ONLY, arr.nbytes)

        prg = cl.Program(
            ctx,
            """
            __kernel void blur(__global const float *in, __global float *out,
                               const int width, const int height) {
                int x = get_global_id(0);
                int y = get_global_id(1);
                if (x >= width || y >= height) return;
                int idx = (y * width + x) * 3;
                for (int c = 0; c < 3; c++) {
                    float sum = 0.0f;
                    int count = 0;
                    for (int dy = -1; dy <= 1; dy++) {
                        int yy = y + dy;
                        if (yy < 0 || yy >= height) continue;
                        for (int dx = -1; dx <= 1; dx++) {
                            int xx = x + dx;
                            if (xx < 0 || xx >= width) continue;
                            sum += in[(yy * width + xx) * 3 + c];
                            count++;
                        }
                    }
                    out[idx + c] = sum / count;
                }
            }
            """,
        ).build()

        prg.blur(queue, (arr.shape[1], arr.shape[0]), None, buf_in, buf_out, np.int32(arr.shape[1]), np.int32(arr.shape[0]))
        result = np.empty_like(arr)
        cl.enqueue_copy(queue, result, buf_out).wait()
        result = result.clip(0, 255).astype(np.uint8)
        return Image.fromarray(result)
    except Exception as exc:
        logger.debug("OpenCL preprocess error: %s", exc)
        raise


def _metal_preprocess(image: "Image.Image") -> "Image.Image":
    """Metal-accelerated preprocessing placeholder.

    On macOS with ``torch`` MPS we can offload simple tensor ops; otherwise
    fall back to CPU.
    """
    try:
        import numpy as np
        import torch  # type: ignore[import-untyped]
        from PIL import Image

        if not torch.backends.mps.is_available():
            raise RuntimeError("MPS not available")

        arr = np.array(image.convert("RGB")).astype(np.float32)
        tensor = torch.from_numpy(arr).to("mps")
        # Simple box blur via avg_pool2d
        tensor = tensor.permute(2, 0, 1).unsqueeze(0)  # NCHW
        blurred = torch.nn.functional.avg_pool2d(tensor, kernel_size=3, stride=1, padding=1, count_include_pad=True)
        blurred = blurred.squeeze(0).permute(1, 2, 0).cpu().numpy()
        blurred = blurred.clip(0, 255).astype(np.uint8)
        return Image.fromarray(blurred)
    except Exception as exc:
        logger.debug("Metal preprocess error: %s", exc)
        raise


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _separable_convolve_3d(arr: Any, kernel: Any) -> Any:
    """Apply a 1-D separable convolution along H and W dimensions (cupy arrays)."""
    import cupy as cp  # type: ignore[import-untyped]

    k = kernel.reshape(1, -1, 1, 1)
    tmp = cp.empty_like(arr)
    for c in range(arr.shape[2]):
        tmp[:, :, c] = cp.apply_along_axis(lambda x: cp.convolve(x, k.ravel(), mode="same"), 0, arr[:, :, c])
    out = cp.empty_like(tmp)
    for c in range(tmp.shape[2]):
        out[:, :, c] = cp.apply_along_axis(lambda x: cp.convolve(x, k.ravel(), mode="same"), 1, tmp[:, :, c])
    return out


def _sobel_gpu(arr: Any) -> Any:
    """Sobel edge magnitude on a cupy array."""
    import cupy as cp  # type: ignore[import-untyped]

    sobel_x = cp.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=cp.float32)
    sobel_y = cp.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=cp.float32)
    mag = cp.zeros_like(arr)
    for c in range(arr.shape[2]):
        gx = cp.apply_along_axis(lambda x: cp.convolve(x, sobel_x[1], mode="same"), 0, arr[:, :, c])
        gx = cp.apply_along_axis(lambda x: cp.convolve(x, sobel_x[:, 1], mode="same"), 1, gx)
        gy = cp.apply_along_axis(lambda x: cp.convolve(x, sobel_y[1], mode="same"), 0, arr[:, :, c])
        gy = cp.apply_along_axis(lambda x: cp.convolve(x, sobel_y[:, 1], mode="same"), 1, gy)
        mag[:, :, c] = cp.sqrt(gx ** 2 + gy ** 2)
    return mag
