from __future__ import annotations

import shutil
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from .models import TraceOptions, TraceResult
from .tracer import trace_image

_SVG_NS = "http://www.w3.org/2000/svg"


@dataclass
class RegionSelector:
    """Describes a region of interest inside a raster image.

    Parameters
    ----------
    x, y:
        Top-left corner of the bounding box (or centre for circles).
    width, height:
        Size of the bounding box.
    shape:
        ``"rect"``, ``"circle"``, or ``"polygon"``.
    polygon_points:
        Required when *shape* is ``"polygon"``. List of ``(x, y)`` vertices
        in **image** coordinates.
    """

    x: int
    y: int
    width: int
    height: int
    shape: str = "rect"
    polygon_points: list[tuple[int, int]] | None = None

    def __post_init__(self) -> None:
        if self.shape not in {"rect", "circle", "polygon"}:
            raise ValueError("shape must be 'rect', 'circle', or 'polygon'.")
        if self.shape == "polygon" and (not self.polygon_points or len(self.polygon_points) < 3):
            raise ValueError("polygon_points must contain at least 3 points when shape='polygon'.")


def crop_region(input_path: Path, region: RegionSelector, output_path: Path) -> Path:
    """Crop a region from *input_path* and save it to *output_path*.

    Supports rectangular, circular, and polygonal masks. The output is always
    a PNG so that transparency information is preserved for non-rectangular
    shapes.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(input_path) as img:
        if region.shape == "rect":
            cropped = img.crop((region.x, region.y, region.x + region.width, region.y + region.height))
        elif region.shape == "circle":
            bbox = (region.x, region.y, region.x + region.width, region.y + region.height)
            cropped = img.crop(bbox).convert("RGBA")
            mask = Image.new("L", cropped.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, region.width, region.height), fill=255)
            cropped.putalpha(mask)
        else:  # polygon
            bbox = (region.x, region.y, region.x + region.width, region.y + region.height)
            cropped = img.crop(bbox).convert("RGBA")
            mask = Image.new("L", cropped.size, 0)
            draw = ImageDraw.Draw(mask)
            local_points = [(px - region.x, py - region.y) for px, py in region.polygon_points]
            draw.polygon(local_points, fill=255)
            cropped.putalpha(mask)

        cropped.save(output_path, format="PNG", optimize=True)

    return output_path


def trace_region(
    input_path: Path,
    region: RegionSelector,
    output_svg: Path,
    options: TraceOptions,
) -> TraceResult:
    """Crop *region* from *input_path*, trace it, and write the SVG to *output_svg*."""
    with tempfile.TemporaryDirectory(prefix="vector-studio-region-") as tmpdir:
        cropped_path = Path(tmpdir) / "cropped.png"
        crop_region(input_path, region, cropped_path)
        return trace_image(cropped_path, output_svg, options)


def merge_region_svg(
    original_svg: Path,
    region_svg: Path,
    region: RegionSelector,
    output_path: Path,
) -> Path:
    """Merge a region SVG back into an original SVG.

    The region content is wrapped in a ``<g>`` group with a
    ``translate(x, y)`` transform so that it maps to the correct location
    inside the original coordinate system.
    """
    original_svg = Path(original_svg)
    region_svg = Path(region_svg)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        orig_tree = ET.parse(original_svg)
    except ET.ParseError as exc:
        raise ValueError(f"Cannot parse original SVG: {exc}") from exc

    try:
        region_tree = ET.parse(region_svg)
    except ET.ParseError as exc:
        raise ValueError(f"Cannot parse region SVG: {exc}") from exc

    orig_root = orig_tree.getroot()
    region_root = region_tree.getroot()

    ET.register_namespace("", _SVG_NS)

    group = ET.Element(f"{{{_SVG_NS}}}g")
    group.set("id", "region-trace")
    group.set("transform", f"translate({region.x}, {region.y})")

    for child in list(region_root):
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag in {"metadata", "title", "desc", "defs"}:
            continue
        group.append(child)

    orig_root.append(group)
    orig_tree.write(output_path, encoding="utf-8", xml_declaration=True)
    return output_path


def region_trace(
    input_path: Path,
    region: RegionSelector,
    output_path: Path,
    options: TraceOptions,
    original_svg: Path | None = None,
) -> TraceResult:
    """High-level helper: trace a region and optionally merge it back.

    If *original_svg* is provided, the traced region SVG is inserted into
    the original SVG at the correct position and *output_path* receives the
    merged result. Otherwise *output_path* contains the standalone region
    trace.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    options = options.validate()

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    if original_svg is not None and not Path(original_svg).exists():
        raise FileNotFoundError(f"Original SVG not found: {original_svg}")

    with tempfile.TemporaryDirectory(prefix="vector-studio-region-") as tmpdir:
        tmpdir_path = Path(tmpdir)
        region_svg_path = tmpdir_path / "region.svg"

        result = trace_region(input_path, region, region_svg_path, options)

        if original_svg is not None:
            merge_region_svg(original_svg, region_svg_path, region, output_path)
            result = TraceResult(
                input_path=input_path,
                svg_path=output_path,
                engine=result.engine,
                elapsed_seconds=result.elapsed_seconds,
                stats=result.stats,
            )
        else:
            shutil.copy2(region_svg_path, output_path)
            result = TraceResult(
                input_path=input_path,
                svg_path=output_path,
                engine=result.engine,
                elapsed_seconds=result.elapsed_seconds,
                stats=result.stats,
            )

    return result
