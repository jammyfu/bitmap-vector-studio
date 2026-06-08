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


@pytest.fixture
def sample_svg_complex(tmp_path: Path) -> Path:
    svg_path = tmp_path / "complex.svg"
    svg_path.write_text(
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
    return svg_path


@pytest.fixture
def sample_image_large(tmp_path: Path) -> Path:
    img_path = tmp_path / "large_image.png"
    img = Image.new("RGB", (6000, 6000), color=(0, 128, 255))
    img.save(img_path, format="PNG")
    return img_path


@pytest.fixture
def sample_image_corrupt(tmp_path: Path) -> Path:
    img_path = tmp_path / "corrupt.png"
    img_path.write_bytes(b"PNG\r\n\x1a\nnot valid image data")
    return img_path


@pytest.fixture
def mock_vtracer():
    from unittest.mock import MagicMock
    fake = MagicMock()
    fake.convert_image_to_svg_py = MagicMock()
    return fake


@pytest.fixture
def mock_potrace():
    from unittest.mock import MagicMock
    fake = MagicMock()
    fake.trace = MagicMock(return_value="<svg><path d=\"M0 0\"/></svg>")
    return fake


@pytest.fixture
def mock_external_editor(tmp_path: Path):
    from unittest.mock import MagicMock
    editor = MagicMock()
    editor.name = "mock_editor"
    editor.executable_path = tmp_path / "mock_editor.exe"
    editor.executable_path.write_text("mock")
    editor.is_available = True
    editor.platform = "windows"
    return editor



@pytest.fixture
def sample_image_bw(tmp_path: Path) -> Path:
    """A small black-and-white PNG for binary preset tests."""
    img_path = tmp_path / "bw_image.png"
    img = Image.new("L", (50, 50), color=128)
    img.save(img_path, format="PNG")
    return img_path


@pytest.fixture
def sample_image_rgba(tmp_path: Path) -> Path:
    """A small RGBA PNG with transparency."""
    img_path = tmp_path / "rgba_image.png"
    img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
    img.save(img_path, format="PNG")
    return img_path


@pytest.fixture
def sample_image_very_small(tmp_path: Path) -> Path:
    """A tiny 1x1 PNG for edge-case tests."""
    img_path = tmp_path / "tiny.png"
    img = Image.new("RGB", (1, 1), color=(0, 0, 0))
    img.save(img_path, format="PNG")
    return img_path


@pytest.fixture
def sample_config_path(tmp_path: Path) -> Path:
    """A valid config file path with logo preset."""
    from vector_studio.config import Config
    cfg = Config(default_preset="logo", export_pdf=True)
    path = tmp_path / "config.json"
    cfg.save(path)
    return path


@pytest.fixture
def mock_trace_result(tmp_path: Path) -> "TraceResult":
    """A reusable mock TraceResult pointing into tmp_path."""
    from vector_studio.models import TraceResult
    svg = tmp_path / "out.svg"
    svg.write_text("<svg></svg>")
    return TraceResult(
        input_path=tmp_path / "in.png",
        svg_path=svg,
        engine="python-vtracer",
        elapsed_seconds=0.5,
        stats={"paths": 3},
    )


@pytest.fixture
def mock_engine_registry():
    """Patch EngineRegistry to return a single mock engine."""
    from unittest.mock import MagicMock, patch
    mock_engine = MagicMock()
    mock_engine.is_available.return_value = True
    mock_engine.get_info.return_value = {"name": "vtracer", "version": "1.0", "available": True}
    with patch("vector_studio.engines.EngineRegistry.get_engine", return_value=mock_engine):
        with patch("vector_studio.engines.EngineRegistry.list_engines", return_value=[
            {"name": "vtracer", "version": "1.0", "available": True, "supported_formats": [".png"], "supported_outputs": [".svg"]},
        ]):
            yield mock_engine
