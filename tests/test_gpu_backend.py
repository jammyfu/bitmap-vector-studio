from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from vector_studio.gpu_backend import (
    GPUBackend,
    _cpu_preprocess,
    detect_gpu,
    gpu_available,
    gpu_preprocess,
)


class TestGPUBackendEnum:
    def test_enum_values(self):
        assert GPUBackend.NONE.value == "none"
        assert GPUBackend.CUDA.value == "cuda"
        assert GPUBackend.METAL.value == "metal"
        assert GPUBackend.OPENCL.value == "opencl"


class TestDetectGPU:
    def test_detect_gpu_returns_none_when_no_libs(self):
        with patch.dict("sys.modules", {"cupy": None, "pycuda": None, "pyopencl": None, "metal": None, "torch": None}):
            result = detect_gpu()
            assert result == GPUBackend.NONE

    def test_detect_gpu_returns_cuda_when_cupy_available(self):
        fake_cupy = MagicMock()
        fake_cupy.cuda.runtime.getDeviceCount.return_value = 1
        with patch.dict("sys.modules", {"cupy": fake_cupy}):
            with patch("vector_studio.gpu_backend.GPUBackend", GPUBackend):
                result = detect_gpu()
                # If cupy is present and has devices, CUDA should be detected
                assert result == GPUBackend.CUDA

    def test_gpu_available_false_when_none(self):
        with patch("vector_studio.gpu_backend.detect_gpu", return_value=GPUBackend.NONE):
            assert gpu_available() is False

    def test_gpu_available_true_when_cuda(self):
        with patch("vector_studio.gpu_backend.detect_gpu", return_value=GPUBackend.CUDA):
            assert gpu_available() is True


class TestGPUPreprocess:
    def test_gpu_preprocess_fallback_to_cpu_when_none(self):
        img = Image.new("RGB", (100, 100), color=(128, 128, 128))
        result = gpu_preprocess(img, backend=GPUBackend.NONE)
        assert isinstance(result, Image.Image)
        assert result.size == (100, 100)

    def test_gpu_preprocess_fallback_on_gpu_failure(self):
        img = Image.new("RGB", (100, 100), color=(128, 128, 128))
        with patch("vector_studio.gpu_backend._cuda_preprocess", side_effect=RuntimeError("boom")):
            result = gpu_preprocess(img, backend=GPUBackend.CUDA)
        assert isinstance(result, Image.Image)
        assert result.size == (100, 100)

    def test_cpu_preprocess_returns_image(self):
        img = Image.new("RGB", (100, 100), color=(128, 128, 128))
        result = _cpu_preprocess(img)
        assert isinstance(result, Image.Image)
        assert result.size == (100, 100)

    def test_gpu_preprocess_auto_detects_backend(self):
        img = Image.new("RGB", (100, 100), color=(128, 128, 128))
        with patch("vector_studio.gpu_backend.detect_gpu", return_value=GPUBackend.NONE):
            result = gpu_preprocess(img)
        assert isinstance(result, Image.Image)
