from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vector_studio.models import TraceOptions, TraceResult
from vector_studio.param_search import (
    ParamGrid,
    quick_search,
    score_result,
    search_best_params,
)


class TestParamGrid:
    def test_default_ranges(self):
        grid = ParamGrid()
        assert grid.color_precision_range == (4, 8)
        assert grid.filter_speckle_range == (0, 8)
        assert grid.layer_difference_range == (8, 32)
        assert grid.corner_threshold_range == (40, 80)
        assert grid.preset_candidates == ["logo", "poster", "photo"]

    def test_generate_combinations_respects_max(self):
        grid = ParamGrid(preset_candidates=["logo"])
        combos = grid.generate_combinations(max_combinations=5)
        assert len(combos) <= 5
        assert len(combos) > 0
        for opts in combos:
            assert isinstance(opts, TraceOptions)

    def test_generate_combinations_with_multiple_presets(self):
        grid = ParamGrid(preset_candidates=["logo", "poster"])
        combos = grid.generate_combinations(max_combinations=10)
        assert len(combos) <= 10
        # Should include both presets.
        presets_used = {opts.colormode for opts in combos}
        assert presets_used  # at least one preset used

    def test_generate_combinations_values_in_range(self):
        grid = ParamGrid(
            color_precision_range=(4, 6),
            filter_speckle_range=(2, 4),
            layer_difference_range=(10, 12),
            corner_threshold_range=(50, 55),
            preset_candidates=["logo"],
        )
        combos = grid.generate_combinations(max_combinations=50)
        for opts in combos:
            assert 4 <= opts.color_precision <= 6
            assert 2 <= opts.filter_speckle <= 4
            assert 10 <= opts.layer_difference <= 12
            assert 50 <= opts.corner_threshold <= 55


class TestScoreResult:
    def test_score_small_fast_svg(self, tmp_path):
        svg = tmp_path / "small.svg"
        svg.write_text(
            '<svg viewBox="0 0 10 10"><path d="M0 0 L10 10" fill="red"/></svg>',
            encoding="utf-8",
        )
        original = tmp_path / "orig.png"
        original.write_bytes(b"x" * 1000)
        score = score_result(svg, original, elapsed=0.5)
        assert score > 0

    def test_score_penalises_large_file(self, tmp_path):
        svg = tmp_path / "big.svg"
        # Create a large SVG with many paths.
        paths = "\n".join(f'<path d="M0 0 L10 10" fill="#{i:06x}"/>' for i in range(100))
        svg.write_text(f'<svg viewBox="0 0 100 100">{paths}</svg>', encoding="utf-8")
        original = tmp_path / "orig.png"
        original.write_bytes(b"x" * 1000)
        score_big = score_result(svg, original, elapsed=1.0)

        small_svg = tmp_path / "small.svg"
        small_svg.write_text(
            '<svg viewBox="0 0 10 10"><path d="M0 0 L10 10" fill="red"/></svg>',
            encoding="utf-8",
        )
        score_small = score_result(small_svg, original, elapsed=1.0)
        assert score_small > score_big

    def test_score_rewards_speed(self, tmp_path):
        svg = tmp_path / "test.svg"
        svg.write_text(
            '<svg viewBox="0 0 10 10"><path d="M0 0 L10 10" fill="red"/></svg>',
            encoding="utf-8",
        )
        original = tmp_path / "orig.png"
        original.write_bytes(b"x" * 1000)
        score_fast = score_result(svg, original, elapsed=0.1)
        score_slow = score_result(svg, original, elapsed=10.0)
        assert score_fast > score_slow

    def test_score_rewards_moderate_colors(self, tmp_path):
        svg = tmp_path / "test.svg"
        # 10 distinct colors = moderate.
        paths = "\n".join(f'<path d="M0 0 L10 10" fill="#{i:06x}"/>' for i in range(10))
        svg.write_text(f'<svg viewBox="0 0 100 100">{paths}</svg>', encoding="utf-8")
        original = tmp_path / "orig.png"
        original.write_bytes(b"x" * 1000)
        score_moderate = score_result(svg, original, elapsed=1.0)

        # Too many colors.
        many_paths = "\n".join(f'<path d="M0 0 L10 10" fill="#{i:06x}"/>' for i in range(100))
        many_svg = tmp_path / "many.svg"
        many_svg.write_text(f'<svg viewBox="0 0 100 100">{many_paths}</svg>', encoding="utf-8")
        score_many = score_result(many_svg, original, elapsed=1.0)
        assert score_moderate > score_many


class TestQuickSearch:
    def test_quick_search_returns_best_preset(self, tmp_path):
        img = tmp_path / "img.png"
        img.write_bytes(b"fake image")
        out_dir = tmp_path / "out"

        mock_result = TraceResult(
            input_path=img,
            svg_path=out_dir / "quick_logo_001.svg",
            engine="python-vtracer",
            elapsed_seconds=1.0,
            stats={"paths": 5},
        )

        with patch("vector_studio.param_search.trace_image", return_value=mock_result):
            with patch("vector_studio.param_search.score_result", return_value=42.0):
                best_name, best_path, best_score = quick_search(img, out_dir)

        assert best_name in ("logo", "poster", "photo")
        assert best_path is not None
        assert isinstance(best_score, float)
        assert best_score == 42.0

    def test_quick_search_all_fail_raises(self, tmp_path):
        img = tmp_path / "img.png"
        img.write_bytes(b"fake image")
        out_dir = tmp_path / "out"

        with patch("vector_studio.param_search.trace_image", side_effect=RuntimeError("boom")):
            with pytest.raises(RuntimeError, match="All preset candidates failed"):
                quick_search(img, out_dir)


class TestSearchBestParams:
    def test_search_best_params_mock(self, tmp_path):
        img = tmp_path / "img.png"
        img.write_bytes(b"fake image")
        out_dir = tmp_path / "out"

        def _fake_trace(input_path, output_path, options):
            output_path.write_text(
                '<svg viewBox="0 0 10 10"><path d="M0 0 L10 10" fill="red"/></svg>',
                encoding="utf-8",
            )
            return TraceResult(
                input_path=input_path,
                svg_path=output_path,
                engine="python-vtracer",
                elapsed_seconds=0.5,
                stats={"paths": 1},
            )

        grid = ParamGrid(preset_candidates=["logo"])
        with patch("vector_studio.param_search.trace_image", side_effect=_fake_trace):
            best_opts, best_path, best_score, all_results = search_best_params(
                img, out_dir, grid=grid, max_combinations=3
            )

        assert best_opts is not None
        assert best_path.exists()
        assert best_score > 0
        assert len(all_results) == 3
        for res in all_results:
            assert "options" in res
            assert "score" in res
            assert "elapsed" in res

    def test_search_best_params_all_fail_raises(self, tmp_path):
        img = tmp_path / "img.png"
        img.write_bytes(b"fake image")
        out_dir = tmp_path / "out"

        grid = ParamGrid(preset_candidates=["logo"])
        with patch("vector_studio.param_search.trace_image", side_effect=RuntimeError("boom")):
            with pytest.raises(RuntimeError, match="All parameter combinations failed"):
                search_best_params(img, out_dir, grid=grid, max_combinations=2)

    def test_search_best_params_some_fail_continues(self, tmp_path):
        img = tmp_path / "img.png"
        img.write_bytes(b"fake image")
        out_dir = tmp_path / "out"

        call_count = 0

        def _fake_trace(input_path, output_path, options):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("boom")
            output_path.write_text(
                '<svg viewBox="0 0 10 10"><path d="M0 0 L10 10" fill="red"/></svg>',
                encoding="utf-8",
            )
            return TraceResult(
                input_path=input_path,
                svg_path=output_path,
                engine="python-vtracer",
                elapsed_seconds=0.5,
                stats={"paths": 1},
            )

        grid = ParamGrid(preset_candidates=["logo"])
        with patch("vector_studio.param_search.trace_image", side_effect=_fake_trace):
            best_opts, best_path, best_score, all_results = search_best_params(
                img, out_dir, grid=grid, max_combinations=2
            )

        assert best_opts is not None
        assert len(all_results) == 2
        assert any("error" in r for r in all_results)
        assert any("error" not in r for r in all_results)
