from __future__ import annotations

import random
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from .models import TraceOptions, TraceResult
from .presets import options_from_preset
from .svg_tools import svg_stats
from .tracer import trace_image


@dataclass
class ParamGrid:
    """Define a parameter search space for bitmap-to-SVG conversion.

    Each range specifies the inclusive lower and upper bounds for a numeric
    parameter.  Preset candidates are tried as base configurations; when a
    preset is selected its built-in defaults are used and only the numeric
    parameters listed here are overridden.
    """

    color_precision_range: tuple[int, int] = (4, 8)
    filter_speckle_range: tuple[int, int] = (0, 8)
    layer_difference_range: tuple[int, int] = (8, 32)
    corner_threshold_range: tuple[int, int] = (40, 80)
    preset_candidates: list[str] = field(default_factory=lambda: ["logo", "poster", "photo"])

    def _random_value(self, low: int, high: int) -> int:
        return random.randint(low, high)

    def generate_combinations(self, max_combinations: int = 20) -> list[TraceOptions]:
        """Generate up to *max_combinations* distinct parameter sets.

        The algorithm first creates a Cartesian grid from the numeric ranges,
        then samples uniformly without replacement until *max_combinations* is
        reached.  Each sampled point is merged with a randomly chosen preset
        candidate so that the resulting options remain valid.
        """
        # Build a coarse grid for each parameter.
        def _steps(low: int, high: int, steps: int = 3) -> list[int]:
            if low == high:
                return [low]
            step = max(1, (high - low) // (steps - 1))
            values = list(range(low, high + 1, step))
            if values[-1] != high:
                values.append(high)
            return values

        color_precision_vals = _steps(*self.color_precision_range)
        filter_speckle_vals = _steps(*self.filter_speckle_range)
        layer_difference_vals = _steps(*self.layer_difference_range)
        corner_threshold_vals = _steps(*self.corner_threshold_range)

        # Cartesian product of all numeric values.
        from itertools import product

        numeric_points = list(
            product(
                color_precision_vals,
                filter_speckle_vals,
                layer_difference_vals,
                corner_threshold_vals,
            )
        )

        # Pair each numeric point with each preset candidate.
        candidates: list[tuple[str, tuple[int, ...]]] = []
        for preset in self.preset_candidates:
            for point in numeric_points:
                candidates.append((preset, point))

        # Shuffle and truncate to max_combinations.
        random.shuffle(candidates)
        selected = candidates[:max_combinations]

        combinations: list[TraceOptions] = []
        for preset_name, (cp, fs, ld, ct) in selected:
            base = options_from_preset(preset_name)
            combinations.append(
                replace(
                    base,
                    color_precision=cp,
                    filter_speckle=fs,
                    layer_difference=ld,
                    corner_threshold=ct,
                )
            )
        return combinations


def _count_colors(svg_path: Path) -> int:
    """Count the number of distinct fill/stroke colors in an SVG."""
    try:
        tree = ET.parse(svg_path)
    except ET.ParseError:
        return 0
    root = tree.getroot()
    colors: set[str] = set()
    for elem in root.iter():
        fill = elem.get("fill")
        stroke = elem.get("stroke")
        style = elem.get("style", "")
        if fill and fill not in ("none", "currentColor", "inherit"):
            colors.add(fill.lower())
        if stroke and stroke not in ("none", "currentColor", "inherit"):
            colors.add(stroke.lower())
        # Very simple inline style parsing for fill/stroke.
        for part in style.split(";"):
            if ":" in part:
                key, val = part.split(":", 1)
                key = key.strip().lower()
                val = val.strip().lower()
                if key in ("fill", "stroke") and val not in ("none", "currentcolor", "inherit"):
                    colors.add(val)
    return len(colors)


def score_result(svg_path: Path, original_path: Path, elapsed: float) -> float:
    """Score an SVG conversion result (higher is better).

    The scoring formula balances file size, path complexity, conversion speed,
    and color richness:

    .. math::
        score = 100 - size\_penalty - path\_penalty + speed\_bonus + color\_bonus

    Parameters
    ----------
    svg_path:
        Path to the generated SVG file.
    original_path:
        Path to the original raster image (used as a size reference).
    elapsed:
        Time in seconds that the conversion took.

    Returns
    -------
    A float score.  Typical values range from roughly 0 to 150.
    """
    stats = svg_stats(svg_path)
    file_bytes = stats.get("file_bytes", 0)
    paths = stats.get("paths", 0) + stats.get("polygons", 0)

    # Size penalty: penalise if SVG is > 500 KB or > 5x the original.
    original_bytes = original_path.stat().st_size if original_path.exists() else 1
    size_ratio = file_bytes / max(original_bytes, 1)
    size_penalty = 0.0
    if file_bytes > 500_000:
        size_penalty += (file_bytes - 500_000) / 10_000
    if size_ratio > 5.0:
        size_penalty += (size_ratio - 5.0) * 5.0

    # Path penalty: penalise if there are > 50 paths.
    path_penalty = 0.0
    if paths > 50:
        path_penalty = (paths - 50) * 0.5

    # Speed bonus: faster is better, capped at +20.
    speed_bonus = max(0.0, 20.0 - elapsed * 2.0)

    # Color bonus: reward a moderate number of distinct colors (5–20 is ideal).
    color_count = _count_colors(svg_path)
    if 5 <= color_count <= 20:
        color_bonus = 15.0
    elif color_count > 20:
        color_bonus = max(0.0, 15.0 - (color_count - 20) * 0.5)
    else:
        color_bonus = color_count * 2.0

    score = 100.0 - size_penalty - path_penalty + speed_bonus + color_bonus
    return score


def search_best_params(
    input_path: Path,
    output_dir: Path,
    grid: ParamGrid | None = None,
    max_combinations: int = 20,
) -> tuple[TraceOptions, Path, float, list[dict[str, Any]]]:
    """Run a parameter search for a single image and return the best result.

    Parameters
    ----------
    input_path:
        Raster image to convert.
    output_dir:
        Directory where intermediate SVGs are saved.
    grid:
        Search space definition.  Defaults to ``ParamGrid()``.
    max_combinations:
        Maximum number of parameter sets to try.

    Returns
    -------
    A 4-tuple: ``(best_options, best_svg_path, best_score, all_results)``.
    *all_results* is a list of dictionaries with keys ``options``, ``svg_path``,
    ``score``, and ``elapsed``.
    """
    grid = grid or ParamGrid()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    combinations = grid.generate_combinations(max_combinations)
    all_results: list[dict[str, Any]] = []

    best_options: TraceOptions | None = None
    best_path: Path | None = None
    best_score = float("-inf")

    for idx, options in enumerate(combinations, start=1):
        out_path = output_dir / f"search_{idx:03d}.svg"
        start = time.perf_counter()
        try:
            trace_image(input_path, out_path, options)
            elapsed = time.perf_counter() - start
            sc = score_result(out_path, input_path, elapsed)
        except Exception as exc:
            elapsed = time.perf_counter() - start
            sc = float("-inf")
            all_results.append(
                {
                    "options": options,
                    "svg_path": out_path,
                    "score": sc,
                    "elapsed": elapsed,
                    "error": str(exc),
                }
            )
            continue

        all_results.append(
            {
                "options": options,
                "svg_path": out_path,
                "score": sc,
                "elapsed": elapsed,
            }
        )

        if sc > best_score:
            best_score = sc
            best_options = options
            best_path = out_path

    if best_options is None or best_path is None:
        raise RuntimeError("All parameter combinations failed.")

    return best_options, best_path, best_score, all_results


def quick_search(
    input_path: Path,
    output_dir: Path,
    preset_candidates: list[str] | None = None,
) -> tuple[str, Path, float]:
    """Quickly try a handful of presets and return the best one.

    Parameters
    ----------
    input_path:
        Raster image to convert.
    output_dir:
        Directory where intermediate SVGs are saved.
    preset_candidates:
        List of preset names to try.  Defaults to ``["logo", "poster", "photo"]``.

    Returns
    -------
    A 3-tuple: ``(best_preset_name, best_svg_path, best_score)``.
    """
    preset_candidates = preset_candidates or ["logo", "poster", "photo"]
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    best_name = ""
    best_path: Path | None = None
    best_score = float("-inf")

    for idx, preset_name in enumerate(preset_candidates, start=1):
        options = options_from_preset(preset_name)
        out_path = output_dir / f"quick_{preset_name}_{idx:03d}.svg"
        start = time.perf_counter()
        try:
            trace_image(input_path, out_path, options)
            elapsed = time.perf_counter() - start
            sc = score_result(out_path, input_path, elapsed)
        except Exception:
            continue

        if sc > best_score:
            best_score = sc
            best_name = preset_name
            best_path = out_path

    if not best_name or best_path is None:
        raise RuntimeError("All preset candidates failed.")

    return best_name, best_path, best_score
