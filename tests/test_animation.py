from pathlib import Path

import json
import pytest

from vector_studio.animation import (
    AnimationBuilder,
    AnimationPreset,
    LottieExporter,
    SVGAnimation,
    list_presets,
)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def sample_svg(tmp_path: Path) -> Path:
    svg = tmp_path / "sample.svg"
    svg.write_text(
        '<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">'
        '<path id="p1" d="M0 0 L100 100" stroke="black"/>'
        '<path id="p2" d="M100 0 L0 100" stroke="red"/>'
        '<rect id="r1" x="10" y="10" width="20" height="20" fill="#00ff00"/>'
        '</svg>',
        encoding="utf-8",
    )
    return svg


@pytest.fixture
def complex_svg(tmp_path: Path) -> Path:
    svg = tmp_path / "complex.svg"
    svg.write_text(
        '<svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">'
        '<g id="group1">'
        '<path d="M0 0 L100 100" fill="#ff0000"/>'
        '<path d="M10 10 L90 90" fill="#ff0000"/>'
        '<rect x="50" y="50" width="20" height="20" fill="#00ff00"/>'
        '</g>'
        '<circle cx="100" cy="100" r="30" fill="#0000ff"/>'
        '<polygon points="0,0 50,0 25,50" fill="#ffff00"/>'
        '</svg>',
        encoding="utf-8",
    )
    return svg


# ------------------------------------------------------------------
# SVGAnimation tests
# ------------------------------------------------------------------

def test_svg_animation_init(sample_svg: Path):
    anim = SVGAnimation(sample_svg)
    assert anim.svg_path == sample_svg


def test_svg_animation_add_draw(sample_svg: Path):
    anim = SVGAnimation(sample_svg)
    result = anim.add_draw_animation("path", duration=2.0, delay=0.5)
    assert result is anim  # chaining
    assert len(anim._animations) == 1
    assert anim._animations[0]["type"] == "draw"


def test_svg_animation_export_smil(sample_svg: Path, tmp_path: Path):
    anim = SVGAnimation(sample_svg)
    anim.add_draw_animation("path", duration=2.0)
    out = tmp_path / "out.svg"
    result = anim.export_smil(out)
    assert result == out
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "stroke-dasharray" in text
    assert "stroke-dashoffset" in text
    assert "<animate" in text


def test_svg_animation_export_css(sample_svg: Path, tmp_path: Path):
    anim = SVGAnimation(sample_svg)
    anim.add_fade_animation("path", duration=1.0)
    out = tmp_path / "out.html"
    result = anim.export_css(out)
    assert result == out
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in text
    assert "@keyframes" in text
    assert "opacity" in text


def test_svg_animation_add_color(sample_svg: Path):
    anim = SVGAnimation(sample_svg)
    anim.add_color_animation("path", "#ff0000", "#00ff00", duration=2.0)
    assert len(anim._animations) == 1
    assert anim._animations[0]["type"] == "color"


def test_svg_animation_add_morph(sample_svg: Path):
    anim = SVGAnimation(sample_svg)
    anim.add_morph_animation("path:first", "path:last", duration=2.0)
    assert len(anim._animations) == 1
    assert anim._animations[0]["type"] == "morph"


# ------------------------------------------------------------------
# LottieExporter tests
# ------------------------------------------------------------------

def test_lottie_exporter_init(complex_svg: Path):
    exporter = LottieExporter(complex_svg)
    assert exporter.svg_path == complex_svg


def test_lottie_exporter_convert(complex_svg: Path):
    exporter = LottieExporter(complex_svg)
    lottie = exporter.convert_to_lottie()
    assert lottie["v"] == "5.5.7"
    assert lottie["w"] == 200
    assert lottie["h"] == 200
    assert len(lottie["layers"]) > 0


def test_lottie_exporter_export_lottie(complex_svg: Path, tmp_path: Path):
    exporter = LottieExporter(complex_svg)
    out = tmp_path / "out.json"
    result = exporter.export_lottie(out)
    assert result == out
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "layers" in data


def test_lottie_exporter_add_animation(complex_svg: Path):
    exporter = LottieExporter(complex_svg)
    exporter.add_lottie_animation("fade")
    assert len(exporter._lottie_animations) == 1


def test_lottie_exporter_export_gif(complex_svg: Path, tmp_path: Path):
    exporter = LottieExporter(complex_svg)
    out = tmp_path / "out.gif"
    result = exporter.export_gif(out, fps=10, duration=1.0)
    assert result == out
    assert out.exists()
    assert out.stat().st_size > 0


# ------------------------------------------------------------------
# AnimationPreset tests
# ------------------------------------------------------------------

def test_animation_preset_dataclass():
    preset = AnimationPreset(name="test", animations=[{"type": "fade"}])
    assert preset.name == "test"
    assert len(preset.animations) == 1


def test_list_presets():
    names = list_presets()
    assert "draw" in names
    assert "reveal" in names
    assert "morph" in names
    assert "pulse" in names
    assert "color_cycle" in names


# ------------------------------------------------------------------
# AnimationBuilder tests
# ------------------------------------------------------------------

def test_animation_builder_load_svg(sample_svg: Path):
    builder = AnimationBuilder().load_svg(sample_svg)
    assert builder._svg_path == sample_svg


def test_animation_builder_apply_preset(sample_svg: Path):
    builder = AnimationBuilder().load_svg(sample_svg).apply_preset("draw")
    assert builder._preset is not None
    assert builder._preset.name == "draw"


def test_animation_builder_apply_preset_unknown(sample_svg: Path):
    builder = AnimationBuilder().load_svg(sample_svg)
    with pytest.raises(ValueError):
        builder.apply_preset("nonexistent")


def test_animation_builder_add_animation(sample_svg: Path):
    builder = (
        AnimationBuilder()
        .load_svg(sample_svg)
        .add_animation(type="fade", element_selector="path", duration=1.0)
    )
    assert len(builder._animations) == 1


def test_animation_builder_build(sample_svg: Path):
    config = (
        AnimationBuilder()
        .load_svg(sample_svg)
        .apply_preset("draw")
        .add_animation(type="fade", element_selector="path", duration=1.0)
        .build()
    )
    assert config["svg_path"] == str(sample_svg)
    assert config["preset"] == "draw"
    assert len(config["animations"]) == 2


def test_animation_builder_export_smil(sample_svg: Path, tmp_path: Path):
    out = tmp_path / "anim.svg"
    result = (
        AnimationBuilder()
        .load_svg(sample_svg)
        .apply_preset("draw")
        .export("smil", out)
    )
    assert result == out
    assert out.exists()


def test_animation_builder_export_css(sample_svg: Path, tmp_path: Path):
    out = tmp_path / "anim.html"
    result = (
        AnimationBuilder()
        .load_svg(sample_svg)
        .apply_preset("reveal")
        .export("css", out)
    )
    assert result == out
    assert out.exists()


def test_animation_builder_export_lottie(complex_svg: Path, tmp_path: Path):
    out = tmp_path / "anim.json"
    result = (
        AnimationBuilder()
        .load_svg(complex_svg)
        .apply_preset("draw")
        .export("lottie", out)
    )
    assert result == out
    assert out.exists()


def test_animation_builder_export_gif(complex_svg: Path, tmp_path: Path):
    out = tmp_path / "anim.gif"
    result = (
        AnimationBuilder()
        .load_svg(complex_svg)
        .apply_preset("reveal")
        .export("gif", out)
    )
    assert result == out
    assert out.exists()


def test_animation_builder_export_unsupported(sample_svg: Path, tmp_path: Path):
    builder = AnimationBuilder().load_svg(sample_svg)
    with pytest.raises(ValueError):
        builder.export("mp4", tmp_path / "x.mp4")


def test_animation_builder_build_without_svg():
    builder = AnimationBuilder()
    with pytest.raises(ValueError):
        builder.build()


# ------------------------------------------------------------------
# Edge cases
# ------------------------------------------------------------------

def test_svg_animation_invalid_svg(tmp_path: Path):
    bad = tmp_path / "bad.svg"
    bad.write_text("not xml", encoding="utf-8")
    with pytest.raises(ValueError):
        SVGAnimation(bad)


def test_lottie_exporter_invalid_svg(tmp_path: Path):
    bad = tmp_path / "bad.svg"
    bad.write_text("not xml", encoding="utf-8")
    with pytest.raises(ValueError):
        LottieExporter(bad)


def test_svg_animation_empty_svg(tmp_path: Path):
    empty = tmp_path / "empty.svg"
    empty.write_text(
        '<svg viewBox="0 0 10 10" xmlns="http://www.w3.org/2000/svg"></svg>',
        encoding="utf-8",
    )
    exporter = LottieExporter(empty)
    lottie = exporter.convert_to_lottie()
    assert lottie["layers"] == []


def test_animation_builder_chaining(sample_svg: Path, tmp_path: Path):
    out = tmp_path / "chain.svg"
    result = (
        AnimationBuilder()
        .load_svg(sample_svg)
        .apply_preset("draw")
        .add_animation(type="color", element_selector="path", from_color="#000", to_color="#fff", duration=1.0)
        .export("smil", out)
    )
    assert result == out
    text = out.read_text(encoding="utf-8")
    assert "stroke-dasharray" in text
    assert "<animate" in text
