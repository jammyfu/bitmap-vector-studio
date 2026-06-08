from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image
from typer.testing import CliRunner

from vector_studio.ai_generation import (
    AIGenerationProcessor,
    StyleEncoder,
    VectorDiffusion,
    VectorGenerator,
    _prompt_seed,
    _quantize_to_palette,
)
from vector_studio.cli import app

runner = CliRunner()


class TestVectorDiffusion:
    def test_diffuse_returns_image_of_requested_size(self):
        diffusion = VectorDiffusion()
        img = diffusion.diffuse("a red circle", steps=10, size=(128, 128))
        assert isinstance(img, Image.Image)
        assert img.size == (128, 128)
        assert img.mode == "RGB"

    def test_diffuse_deterministic_for_same_prompt(self):
        diffusion = VectorDiffusion()
        img1 = diffusion.diffuse("test prompt", steps=10, size=(64, 64))
        img2 = diffusion.diffuse("test prompt", steps=10, size=(64, 64))
        assert img1.tobytes() == img2.tobytes()

    def test_diffuse_different_prompts_different_outputs(self):
        diffusion = VectorDiffusion()
        img1 = diffusion.diffuse("prompt one", steps=10, size=(64, 64))
        img2 = diffusion.diffuse("prompt two", steps=10, size=(64, 64))
        assert img1.tobytes() != img2.tobytes()


class TestStyleEncoder:
    def test_encode_style_returns_14d_vector(self):
        encoder = StyleEncoder()
        img = Image.new("RGB", (50, 50), color=(100, 150, 200))
        vec = encoder.encode_style(img)
        assert isinstance(vec, list)
        assert len(vec) == 14
        assert all(isinstance(v, float) for v in vec)

    def test_apply_style_changes_image(self):
        encoder = StyleEncoder()
        style_img = Image.new("RGB", (50, 50), color=(255, 0, 0))
        target = Image.new("RGB", (50, 50), color=(0, 0, 255))
        vec = encoder.encode_style(style_img)
        result = encoder.apply_style(target, vec)
        assert result.mode == "RGB"
        assert result.size == target.size
        # Result should be closer to red than pure blue after style transfer
        arr = np.array(result)
        assert arr[:, :, 0].mean() > arr[:, :, 2].mean()

    def test_apply_style_rejects_short_vector(self):
        encoder = StyleEncoder()
        target = Image.new("RGB", (10, 10))
        with pytest.raises(ValueError, match="at least 6 elements"):
            encoder.apply_style(target, [0.5, 0.5])


class TestVectorGenerator:
    def test_generate_from_text_all_styles(self):
        generator = VectorGenerator()
        for style in ("flat", "line", "gradient", "3d", "sketch"):
            img = generator.generate_from_text("a star", style=style, size=(64, 64))
            assert img.mode == "RGB"
            assert img.size == (64, 64)

    def test_generate_from_text_unknown_style_raises(self):
        generator = VectorGenerator()
        with pytest.raises(ValueError, match="Unknown style"):
            generator.generate_from_text("test", style="neon")

    def test_generate_from_image_preserves_size(self):
        generator = VectorGenerator()
        ref = Image.new("RGB", (80, 60), color=(128, 128, 128))
        result = generator.generate_from_image(ref, prompt="test")
        assert result.size == ref.size
        assert result.mode == "RGB"

    def test_generate_icon_square_output(self):
        generator = VectorGenerator()
        img = generator.generate_icon("gear", style="flat")
        assert img.size == (256, 256)
        assert img.mode == "RGB"

    def test_generate_icon_unknown_style_raises(self):
        generator = VectorGenerator()
        with pytest.raises(ValueError, match="Unknown icon style"):
            generator.generate_icon("gear", style="neon")

    def test_generate_logo_output_size(self):
        generator = VectorGenerator()
        img = generator.generate_logo("tech", style="minimal")
        assert img.size == (512, 256)
        assert img.mode == "RGB"

    def test_generate_logo_unknown_style_raises(self):
        generator = VectorGenerator()
        with pytest.raises(ValueError, match="Unknown logo style"):
            generator.generate_logo("tech", style="neon")

    def test_generate_illustration_output_size(self):
        generator = VectorGenerator()
        img = generator.generate_illustration("forest", style="cartoon")
        assert img.size == (512, 512)
        assert img.mode == "RGB"

    def test_generate_illustration_unknown_style_raises(self):
        generator = VectorGenerator()
        with pytest.raises(ValueError, match="Unknown illustration style"):
            generator.generate_illustration("forest", style="neon")

    def test_generate_from_text_with_mock_diffusion(self, tmp_path: Path):
        """Mock the diffusion to return a known image and verify post-processing."""
        generator = VectorGenerator()
        fake_base = Image.new("RGB", (64, 64), color=(200, 200, 200))
        with patch.object(generator.diffusion, "diffuse", return_value=fake_base) as mock_diffuse:
            img = generator.generate_from_text("mocked", style="flat", size=(64, 64))
        mock_diffuse.assert_called_once()
        assert img.mode == "RGB"
        assert img.size == (64, 64)


class TestAIGenerationProcessor:
    def test_generate_text_task(self):
        processor = AIGenerationProcessor()
        with patch.object(processor.generator, "generate_from_text", return_value=Image.new("RGB", (64, 64))) as mock_gen:
            result = processor.generate("text", "hello", style="flat", size=(64, 64))
        mock_gen.assert_called_once_with("hello", style="flat", size=(64, 64))
        assert result.size == (64, 64)

    def test_generate_icon_task(self):
        processor = AIGenerationProcessor()
        with patch.object(processor.generator, "generate_icon", return_value=Image.new("RGB", (256, 256))) as mock_gen:
            result = processor.generate("icon", "settings")
        mock_gen.assert_called_once_with("settings")
        assert result.size == (256, 256)

    def test_generate_unknown_task_raises(self):
        processor = AIGenerationProcessor()
        with pytest.raises(ValueError, match="Unknown task"):
            processor.generate("magic", "test")


class TestHelpers:
    def test_prompt_seed_deterministic(self):
        assert _prompt_seed("hello") == _prompt_seed("hello")
        assert _prompt_seed("hello") != _prompt_seed("world")

    def test_quantize_to_palette(self):
        img = Image.new("RGB", (10, 10), color=(123, 123, 123))
        palette = [(0, 0, 0), (255, 255, 255)]
        result = _quantize_to_palette(img, palette)
        assert result.mode == "RGB"
        # Mid-gray should map to one of the two palette colors
        px = result.getpixel((0, 0))
        assert px in palette


class TestGenerateCLI:
    def test_generate_text_command(self, tmp_path: Path):
        out = tmp_path / "out.png"
        with patch("vector_studio.ai_generation.VectorGenerator") as mock_cls:
            mock_instance = mock_cls.return_value
            mock_instance.generate_from_text.return_value = Image.new("RGB", (64, 64))
            result = runner.invoke(app, ["generate", "text", "a cat", "--output", str(out), "--width", "64", "--height", "64"])
        assert result.exit_code == 0
        assert "Generated" in result.output
        mock_instance.generate_from_text.assert_called_once()

    def test_generate_image_command(self, tmp_path: Path):
        img = tmp_path / "ref.png"
        Image.new("RGB", (50, 50)).save(img, format="PNG")
        out = tmp_path / "out.png"
        with patch("vector_studio.ai_generation.VectorGenerator") as mock_cls:
            mock_instance = mock_cls.return_value
            mock_instance.generate_from_image.return_value = Image.new("RGB", (50, 50))
            result = runner.invoke(app, ["generate", "image", str(img), "--output", str(out)])
        assert result.exit_code == 0
        assert "Generated" in result.output
        mock_instance.generate_from_image.assert_called_once()

    def test_generate_icon_command(self, tmp_path: Path):
        out = tmp_path / "icon.png"
        with patch("vector_studio.ai_generation.VectorGenerator") as mock_cls:
            mock_instance = mock_cls.return_value
            mock_instance.generate_icon.return_value = Image.new("RGB", (256, 256))
            result = runner.invoke(app, ["generate", "icon", "gear", "--output", str(out)])
        assert result.exit_code == 0
        assert "Generated icon" in result.output
        mock_instance.generate_icon.assert_called_once_with("gear", style="flat")

    def test_generate_logo_command(self, tmp_path: Path):
        out = tmp_path / "logo.png"
        with patch("vector_studio.ai_generation.VectorGenerator") as mock_cls:
            mock_instance = mock_cls.return_value
            mock_instance.generate_logo.return_value = Image.new("RGB", (512, 256))
            result = runner.invoke(app, ["generate", "logo", "tech", "--output", str(out)])
        assert result.exit_code == 0
        assert "Generated logo" in result.output
        mock_instance.generate_logo.assert_called_once_with("tech", style="minimal")

    def test_generate_illustration_command(self, tmp_path: Path):
        out = tmp_path / "ill.png"
        with patch("vector_studio.ai_generation.VectorGenerator") as mock_cls:
            mock_instance = mock_cls.return_value
            mock_instance.generate_illustration.return_value = Image.new("RGB", (512, 512))
            result = runner.invoke(app, ["generate", "illustration", "forest", "--output", str(out)])
        assert result.exit_code == 0
        assert "Generated illustration" in result.output
        mock_instance.generate_illustration.assert_called_once_with("forest", style="cartoon")

    def test_generate_text_missing_prompt_fails(self):
        result = runner.invoke(app, ["generate", "text"])
        assert result.exit_code != 0

    def test_generate_image_missing_file_fails(self):
        result = runner.invoke(app, ["generate", "image", "/nonexistent/file.png"])
        assert result.exit_code != 0
