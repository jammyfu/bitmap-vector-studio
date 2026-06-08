from pathlib import Path

import pytest

from vector_studio.svg_tools import (
    analyze_svg_structure,
    extract_color_palette,
    name_svg_layers,
    suggest_optimization,
)


SAMPLE_SVG = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <g id="group1">
    <path d="M0 0 L10 10" fill="#ff0000" stroke="#000000"/>
    <path d="M10 10 L20 0" fill="#00ff00" style="stroke:#0000ff"/>
  </g>
  <rect x="50" y="50" width="10" height="10" fill="#ff0000"/>
  <polygon points="0,0 10,0 5,10" fill="#ffff00"/>
</svg>
"""


def _write_sample(tmp_path: Path) -> Path:
    svg = tmp_path / "sample.svg"
    svg.write_text(SAMPLE_SVG, encoding="utf-8")
    return svg


def test_name_svg_layers_adds_ids_and_labels(tmp_path: Path):
    svg = _write_sample(tmp_path)
    name_svg_layers(svg, strategy="color")
    text = svg.read_text(encoding="utf-8")
    assert "inkscape:label=" in text
    assert "sodipodi:insensitive=" in text
    assert 'id="layer_' in text or 'id="group1"' in text


def test_name_svg_layers_color_strategy(tmp_path: Path):
    svg = _write_sample(tmp_path)
    name_svg_layers(svg, strategy="color")
    text = svg.read_text(encoding="utf-8")
    # Red fill should produce a layer name containing ff0000
    assert "ff0000" in text


def test_name_svg_layers_order_strategy(tmp_path: Path):
    svg = _write_sample(tmp_path)
    name_svg_layers(svg, strategy="order")
    text = svg.read_text(encoding="utf-8")
    assert "layer_1_background" in text


def test_name_svg_layers_invalid_strategy(tmp_path: Path):
    svg = _write_sample(tmp_path)
    with pytest.raises(ValueError, match="strategy must be"):
        name_svg_layers(svg, strategy="invalid")


def test_analyze_svg_structure_returns_expected_shape(tmp_path: Path):
    svg = _write_sample(tmp_path)
    info = analyze_svg_structure(svg)
    assert info["viewBox"] == "0 0 100 100"
    assert info["width"] == "100"
    assert info["height"] == "100"
    assert info["total_paths"] == 2
    assert info["total_groups"] == 1
    assert len(info["layers"]) == 5  # g + 2 paths + rect + polygon
    assert set(info["color_palette"]) == {"#ff0000", "#00ff00", "#0000ff", "#000000", "#ffff00"}


def test_analyze_svg_structure_layer_details(tmp_path: Path):
    svg = _write_sample(tmp_path)
    info = analyze_svg_structure(svg)
    layers = info["layers"]
    # First layer is the group
    assert layers[0]["type"] == "g"
    assert layers[0]["path_count"] == 2
    # Find the rect layer
    rect_layer = next(l for l in layers if l["type"] == "rect")
    assert rect_layer["fill"] == "#ff0000"
    assert rect_layer["bbox"] == [50.0, 50.0, 10.0, 10.0]


def test_analyze_svg_structure_graceful_on_bad_file(tmp_path: Path):
    bad = tmp_path / "bad.svg"
    bad.write_text("not xml", encoding="utf-8")
    info = analyze_svg_structure(bad)
    assert info["viewBox"] is None
    assert info["layers"] == []


def test_extract_color_palette_counts_and_sorting(tmp_path: Path):
    svg = _write_sample(tmp_path)
    colors, counts = extract_color_palette(svg)
    assert "#ff0000" in colors
    assert counts["#ff0000"] >= 2  # fill on path + rect
    # Sorted by descending count
    assert counts[colors[0]] >= counts[colors[-1]]


def test_suggest_optimization_large_file(tmp_path: Path):
    svg = tmp_path / "big.svg"
    # Create a large SVG with many paths to exceed 100 KB
    paths = "\n".join(f'<path d="M{i} 0 L{i+1} 1 C{i+2} 2 {i+3} 3 {i+4} 4 Z" fill="#ff0000" stroke="#000000" stroke-width="2"/>' for i in range(1200))
    content = f'<svg viewBox="0 0 100 100">{paths}</svg>'
    svg.write_text(content, encoding="utf-8")
    suggestions = suggest_optimization(svg)
    assert any("路径数过多" in s for s in suggestions)
    assert any("文件较大" in s for s in suggestions)


def test_suggest_optimization_single_path_layers(tmp_path: Path):
    svg = tmp_path / "layers.svg"
    groups = "\n".join(f'<g><path d="M{i} 0 L{i+1} 1" fill="#ff0000"/></g>' for i in range(10))
    content = f'<svg viewBox="0 0 100 100">{groups}</svg>'
    svg.write_text(content, encoding="utf-8")
    suggestions = suggest_optimization(svg)
    assert any("单路径图层" in s for s in suggestions)


def test_suggest_optimization_empty_svg(tmp_path: Path):
    svg = tmp_path / "empty.svg"
    svg.write_text('<svg viewBox="0 0 10 10"></svg>', encoding="utf-8")
    suggestions = suggest_optimization(svg)
    assert any("未检测到" in s for s in suggestions)
