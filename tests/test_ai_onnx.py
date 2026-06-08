from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from vector_studio.ai_onnx import (
    AIProcessor,
    ImageSegmenter,
    MODEL_REGISTRY,
    ONNXModelManager,
    StyleTransfer,
    SuperResolution,
)


class TestONNXModelManager:
    def test_default_models_dir_created(self, tmp_path: Path):
        manager = ONNXModelManager(models_dir=tmp_path / "models")
        assert manager.models_dir.exists()

    def test_list_available_models_empty_when_none_downloaded(self, tmp_path: Path):
        manager = ONNXModelManager(models_dir=tmp_path)
        assert manager.list_available_models() == []

    def test_is_model_available_true_when_file_exists(self, tmp_path: Path):
        manager = ONNXModelManager(models_dir=tmp_path)
        (tmp_path / "unet-lite.onnx").write_text("fake")
        assert manager.is_model_available("unet-lite") is True

    def test_is_model_available_false_when_missing(self, tmp_path: Path):
        manager = ONNXModelManager(models_dir=tmp_path)
        assert manager.is_model_available("unet-lite") is False

    def test_download_model_writes_file(self, tmp_path: Path):
        manager = ONNXModelManager(models_dir=tmp_path)
        fake_url = "http://example.com/fake.onnx"

        def fake_urlretrieve(url, filename):
            Path(filename).write_text("fake onnx data")

        with patch("urllib.request.urlretrieve", side_effect=fake_urlretrieve) as mock_retrieve:
            path = manager.download_model("unet-lite", url=fake_url)
        assert path.exists()
        mock_retrieve.assert_called_once()

    def test_download_model_raises_on_unknown_model_without_url(self, tmp_path: Path):
        manager = ONNXModelManager(models_dir=tmp_path)
        with pytest.raises(ValueError, match="Unknown model"):
            manager.download_model("nonexistent")

    def test_load_model_raises_when_onnx_missing(self, tmp_path: Path):
        manager = ONNXModelManager(models_dir=tmp_path)
        (tmp_path / "dummy.onnx").write_text("fake")
        with patch("vector_studio.ai_onnx._ONNX_AVAILABLE", False):
            with patch("vector_studio.ai_onnx.ort", None):
                with pytest.raises(RuntimeError, match="ONNX Runtime is not installed"):
                    manager.load_model(tmp_path / "dummy.onnx")


class TestImageSegmenter:
    def test_fallback_mask_when_model_missing(self, tmp_path: Path):
        manager = ONNXModelManager(models_dir=tmp_path)
        segmenter = ImageSegmenter(manager)
        img = Image.new("RGB", (100, 100), color=(200, 200, 200))
        mask = segmenter.segment(img, model_name="unet-lite")
        assert mask.mode == "L"
        assert mask.size == (100, 100)

    def test_segment_and_simplify_returns_rgba(self, tmp_path: Path):
        manager = ONNXModelManager(models_dir=tmp_path)
        segmenter = ImageSegmenter(manager)
        img = Image.new("RGB", (50, 50), color=(255, 0, 0))
        result = segmenter.segment_and_simplify(img)
        assert result.mode == "RGBA"
        assert result.size == (50, 50)

    def test_onnx_segment_path_with_mock_session(self, tmp_path: Path):
        manager = ONNXModelManager(models_dir=tmp_path)
        (tmp_path / "unet-lite.onnx").write_text("fake")
        segmenter = ImageSegmenter(manager)

        fake_output = MagicMock()
        fake_output.name = "input"
        fake_session = MagicMock()
        fake_session.get_inputs.return_value = [fake_output]

        # Create a real numpy-like array for the output
        import numpy as np
        fake_mask = np.random.rand(256, 256).astype(np.float32)
        fake_session.run.return_value = [fake_mask]

        segmenter._session = fake_session
        with patch("vector_studio.ai_onnx._ONNX_AVAILABLE", True):
            with patch("vector_studio.ai_onnx.np", np):
                img = Image.new("RGB", (100, 100))
                mask = segmenter._onnx_segment(img, "unet-lite")
                assert mask.size == (100, 100)
                assert mask.mode == "L"


class TestStyleTransfer:
    def test_transfer_unknown_style_raises(self, tmp_path: Path):
        manager = ONNXModelManager(models_dir=tmp_path)
        transfer = StyleTransfer(manager)
        img = Image.new("RGB", (64, 64))
        with pytest.raises(ValueError, match="Unknown style"):
            transfer.transfer(img, style="neon")

    def test_fallback_sketch_style(self, tmp_path: Path):
        manager = ONNXModelManager(models_dir=tmp_path)
        transfer = StyleTransfer(manager)
        img = Image.new("RGB", (64, 64), color=(128, 128, 128))
        result = transfer.transfer(img, style="sketch")
        assert result.mode == "RGB"
        assert result.size == (64, 64)

    def test_preprocess_for_vectorize(self, tmp_path: Path):
        manager = ONNXModelManager(models_dir=tmp_path)
        transfer = StyleTransfer(manager)
        img = Image.new("RGB", (64, 64))
        result = transfer.preprocess_for_vectorize(img)
        assert result.mode == "RGB"
        assert result.size == (64, 64)

    def test_fallback_oil_style(self, tmp_path: Path):
        manager = ONNXModelManager(models_dir=tmp_path)
        transfer = StyleTransfer(manager)
        img = Image.new("RGB", (64, 64))
        result = transfer.transfer(img, style="oil")
        assert result.mode == "RGB"

    def test_fallback_watercolor_style(self, tmp_path: Path):
        manager = ONNXModelManager(models_dir=tmp_path)
        transfer = StyleTransfer(manager)
        img = Image.new("RGB", (64, 64))
        result = transfer.transfer(img, style="watercolor")
        assert result.mode == "RGB"

    def test_fallback_cartoon_style(self, tmp_path: Path):
        manager = ONNXModelManager(models_dir=tmp_path)
        transfer = StyleTransfer(manager)
        img = Image.new("RGB", (64, 64))
        result = transfer.transfer(img, style="cartoon")
        assert result.mode == "RGB"


class TestSuperResolution:
    def test_fallback_upscale_when_model_missing(self, tmp_path: Path):
        manager = ONNXModelManager(models_dir=tmp_path)
        sr = SuperResolution(manager)
        img = Image.new("RGB", (50, 50))
        result = sr.upscale(img, scale=2)
        assert result.size == (100, 100)

    def test_fallback_upscale_scale_4(self, tmp_path: Path):
        manager = ONNXModelManager(models_dir=tmp_path)
        sr = SuperResolution(manager)
        img = Image.new("RGB", (25, 25))
        result = sr.upscale(img, scale=4)
        assert result.size == (100, 100)


class TestAIProcessor:
    def test_process_segment_task(self, tmp_path: Path):
        manager = ONNXModelManager(models_dir=tmp_path)
        processor = AIProcessor(manager)
        img = Image.new("RGB", (64, 64))
        result = processor.process(img, "segment")
        assert result.mode == "L"

    def test_process_style_transfer_task(self, tmp_path: Path):
        manager = ONNXModelManager(models_dir=tmp_path)
        processor = AIProcessor(manager)
        img = Image.new("RGB", (64, 64))
        result = processor.process(img, "style_transfer", style="sketch")
        assert result.mode == "RGB"

    def test_process_upscale_task(self, tmp_path: Path):
        manager = ONNXModelManager(models_dir=tmp_path)
        processor = AIProcessor(manager)
        img = Image.new("RGB", (50, 50))
        result = processor.process(img, "upscale", scale=2)
        assert result.size == (100, 100)

    def test_process_auto_enhance_task(self, tmp_path: Path):
        manager = ONNXModelManager(models_dir=tmp_path)
        processor = AIProcessor(manager)
        img = Image.new("RGB", (50, 50))
        result = processor.process(img, "auto_enhance")
        assert result.size == (100, 100)

    def test_process_unknown_task_raises(self, tmp_path: Path):
        manager = ONNXModelManager(models_dir=tmp_path)
        processor = AIProcessor(manager)
        img = Image.new("RGB", (64, 64))
        with pytest.raises(ValueError, match="Unknown task"):
            processor.process(img, "magic")

    def test_model_registry_has_expected_keys(self):
        assert "unet-lite" in MODEL_REGISTRY
        assert "esrgan-lite" in MODEL_REGISTRY
        assert "style-sketch" in MODEL_REGISTRY
        assert "style-oil" in MODEL_REGISTRY
        assert "style-watercolor" in MODEL_REGISTRY
        assert "style-cartoon" in MODEL_REGISTRY
