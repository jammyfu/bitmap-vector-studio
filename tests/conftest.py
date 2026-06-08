import pytest
from pathlib import Path
from PIL import Image
from vector_studio.models import TraceOptions


@pytest.fixture
def sample_trace_options() -> TraceOptions:
    return TraceOptions(
        colormode="color",
        hierarchical="stacked",
        mode="spline",
        filter_speckle=4,
        color_precision=6,
        layer_difference=16,
        corner_threshold=60,
        length_threshold=4.0,
        max_iterations=10,
        splice_threshold=45,
        path_precision=3,
        denoise=False,
        posterize=None,
        max_input_side=None,
        alpha_background="#ffffff",
    )


@pytest.fixture
def sample_image(tmp_path: Path) -> Path:
    img_path = tmp_path / "test_image.png"
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    img.save(img_path, format="PNG")
    return img_path


@pytest.fixture
def sample_svg(tmp_path: Path) -> Path:
    svg_path = tmp_path / "test_image.svg"
    svg_path.write_text(
        '<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">'
        '<path d="M0 0 L100 100" stroke="black"/>'
        "</svg>",
        encoding="utf-8",
    )
    return svg_path
