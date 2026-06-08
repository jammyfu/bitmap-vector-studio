from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from vector_studio.engine_orchestrator import EngineOrchestrator
from vector_studio.models import TraceOptions, TraceResult


class TestEngineOrchestratorAnalyze:
    def test_analyze_photo_image(self, tmp_path: Path):
        orch = EngineOrchestrator()
        img_path = tmp_path / "photo.png"
        # Use a noisy image to avoid scan classification
        import random
        img = Image.new("RGB", (2000, 1500))
        pixels = img.load()
        for i in range(2000):
            for j in range(1500):
                pixels[i, j] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        img.save(img_path, format="PNG")
        analysis = orch.analyze_image(img_path)
        assert analysis["image_type"] == "photo"
        assert analysis["is_likely_photo"] is True
        assert analysis["width"] == 2000
        assert analysis["height"] == 1500

    def test_analyze_logo_image(self, tmp_path: Path):
        orch = EngineOrchestrator()
        img_path = tmp_path / "logo.png"
        img = Image.new("RGBA", (200, 200), color=(255, 0, 0, 128))
        img.save(img_path, format="PNG")
        analysis = orch.analyze_image(img_path)
        assert analysis["image_type"] == "logo"
        assert analysis["is_likely_logo"] is True

    def test_analyze_scan_image(self, tmp_path: Path):
        orch = EngineOrchestrator()
        img_path = tmp_path / "scan.png"
        img = Image.new("L", (800, 1000), color=240)
        img.save(img_path, format="PNG")
        analysis = orch.analyze_image(img_path)
        assert analysis["image_type"] == "scan"
        assert analysis["is_likely_scan"] is True

    def test_analyze_returns_expected_keys(self, tmp_path: Path):
        orch = EngineOrchestrator()
        img_path = tmp_path / "test.png"
        Image.new("RGB", (100, 100)).save(img_path, format="PNG")
        analysis = orch.analyze_image(img_path)
        expected_keys = {
            "image_type", "complexity", "color_count", "edge_density",
            "aspect_ratio", "is_likely_logo", "is_likely_photo",
            "is_likely_scan", "width", "height",
        }
        assert expected_keys.issubset(analysis.keys())


class TestEngineOrchestratorRecommend:
    def test_recommend_pipeline_for_photo(self, tmp_path: Path):
        orch = EngineOrchestrator()
        img_path = tmp_path / "photo.png"
        # Use a noisy image to avoid scan classification
        import random
        img = Image.new("RGB", (2000, 1500))
        pixels = img.load()
        for i in range(2000):
            for j in range(1500):
                pixels[i, j] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        img.save(img_path, format="PNG")
        pipeline = orch.recommend_pipeline(img_path)
        steps = [p["step"] for p in pipeline]
        assert "ai_upscale" in steps
        assert "ai_style" in steps
        assert "vectorize" in steps
        assert pipeline[-1]["engine"] == "vtracer"

    def test_recommend_pipeline_for_logo(self, tmp_path: Path):
        orch = EngineOrchestrator()
        img_path = tmp_path / "logo.png"
        Image.new("RGBA", (200, 200), color=(255, 0, 0, 128)).save(img_path, format="PNG")
        pipeline = orch.recommend_pipeline(img_path)
        steps = [p["step"] for p in pipeline]
        assert "ai_segment" in steps
        assert "vectorize" in steps
        assert pipeline[-1]["engine"] == "potrace"

    def test_recommend_pipeline_for_scan(self, tmp_path: Path):
        orch = EngineOrchestrator()
        img_path = tmp_path / "scan.png"
        Image.new("L", (800, 1000), color=240).save(img_path, format="PNG")
        pipeline = orch.recommend_pipeline(img_path)
        steps = [p["step"] for p in pipeline]
        assert "ai_enhance" in steps
        assert "vectorize" in steps
        assert pipeline[-1]["engine"] == "vtracer"

    def test_recommend_pipeline_for_unknown_defaults_to_vtracer(self, tmp_path: Path):
        orch = EngineOrchestrator()
        img_path = tmp_path / "complex.png"
        # Create a noisy image to avoid scan classification
        import random
        img = Image.new("RGB", (500, 500))
        pixels = img.load()
        for i in range(500):
            for j in range(500):
                pixels[i, j] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        img.save(img_path, format="PNG")
        pipeline = orch.recommend_pipeline(img_path)
        assert len(pipeline) == 1
        assert pipeline[0]["step"] == "vectorize"
        assert pipeline[0]["engine"] == "vtracer"


class TestEngineOrchestratorRunPipeline:
    def test_run_pipeline_with_vectorize_only(self, tmp_path: Path):
        orch = EngineOrchestrator()
        img_path = tmp_path / "input.png"
        out_path = tmp_path / "output.svg"
        Image.new("RGB", (100, 100)).save(img_path, format="PNG")
        out_path.write_text("<svg></svg>")

        mock_result = TraceResult(
            input_path=img_path,
            svg_path=out_path,
            engine="vtracer",
            elapsed_seconds=0.5,
            stats={},
        )

        with patch("vector_studio.engine_orchestrator.trace_image", return_value=mock_result):
            result = orch.run_pipeline(
                img_path,
                [{"step": "vectorize", "engine": "vtracer", "kwargs": {}}],
                out_path,
            )
        assert result.svg_path == out_path
        assert result.input_path == img_path
        assert "orchestrator" in result.engine

    def test_run_pipeline_with_ai_steps(self, tmp_path: Path):
        orch = EngineOrchestrator()
        img_path = tmp_path / "input.png"
        out_path = tmp_path / "output.svg"
        Image.new("RGB", (100, 100)).save(img_path, format="PNG")
        out_path.write_text("<svg></svg>")

        mock_result = TraceResult(
            input_path=img_path,
            svg_path=out_path,
            engine="vtracer",
            elapsed_seconds=0.5,
            stats={},
        )

        with patch("vector_studio.engine_orchestrator.trace_image", return_value=mock_result):
            with patch.object(orch.ai, "process", side_effect=lambda img, task, **kw: img):
                result = orch.run_pipeline(
                    img_path,
                    [
                        {"step": "ai_upscale", "task": "upscale", "kwargs": {"scale": 2}},
                        {"step": "vectorize", "engine": "vtracer", "kwargs": {}},
                    ],
                    out_path,
                )
        assert result.svg_path == out_path

    def test_run_pipeline_continues_on_ai_failure(self, tmp_path: Path):
        orch = EngineOrchestrator()
        img_path = tmp_path / "input.png"
        out_path = tmp_path / "output.svg"
        Image.new("RGB", (100, 100)).save(img_path, format="PNG")
        out_path.write_text("<svg></svg>")

        mock_result = TraceResult(
            input_path=img_path,
            svg_path=out_path,
            engine="vtracer",
            elapsed_seconds=0.5,
            stats={},
        )

        with patch("vector_studio.engine_orchestrator.trace_image", return_value=mock_result):
            with patch.object(orch.ai, "process", side_effect=RuntimeError("boom")):
                result = orch.run_pipeline(
                    img_path,
                    [
                        {"step": "ai_upscale", "task": "upscale", "kwargs": {"scale": 2}},
                        {"step": "vectorize", "engine": "vtracer", "kwargs": {}},
                    ],
                    out_path,
                )
        assert result.svg_path == out_path

    def test_run_pipeline_no_vectorize_step_falls_back(self, tmp_path: Path):
        orch = EngineOrchestrator()
        img_path = tmp_path / "input.png"
        out_path = tmp_path / "output.svg"
        Image.new("RGB", (100, 100)).save(img_path, format="PNG")
        out_path.write_text("<svg></svg>")

        mock_result = TraceResult(
            input_path=img_path,
            svg_path=out_path,
            engine="vtracer",
            elapsed_seconds=0.5,
            stats={},
        )

        with patch("vector_studio.engine_orchestrator.trace_image", return_value=mock_result):
            result = orch.run_pipeline(
                img_path,
                [{"step": "ai_enhance", "task": "auto_enhance", "kwargs": {}}],
                out_path,
            )
        assert result.svg_path == out_path
        assert "orchestrator" in result.engine

    def test_run_pipeline_passes_trace_options(self, tmp_path: Path):
        orch = EngineOrchestrator()
        img_path = tmp_path / "input.png"
        out_path = tmp_path / "output.svg"
        Image.new("RGB", (100, 100)).save(img_path, format="PNG")
        out_path.write_text("<svg></svg>")
        opts = TraceOptions(colormode="binary")

        mock_result = TraceResult(
            input_path=img_path,
            svg_path=out_path,
            engine="vtracer",
            elapsed_seconds=0.5,
            stats={},
        )

        with patch("vector_studio.engine_orchestrator.trace_image", return_value=mock_result) as mock_trace:
            orch.run_pipeline(
                img_path,
                [{"step": "vectorize", "engine": "vtracer", "kwargs": {}}],
                out_path,
                trace_options=opts,
            )
        passed_opts = mock_trace.call_args[0][2]
        assert passed_opts.colormode == "binary"
