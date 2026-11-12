from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from vector_studio.cli import app


@pytest.mark.parametrize("prefix", [["search"], ["search", "params"]])
def test_parameter_search_supports_legacy_and_explicit_routes(tmp_path: Path, prefix):
    image = tmp_path / "image.png"
    image.write_bytes(b"test input handled by mocked search")
    output = tmp_path / "results"
    with (
        patch(
            "vector_studio.cli.quick_search", return_value=("logo", output / "best.svg", 42.0)
        ) as search,
        patch("vector_studio.cli.svg_stats", return_value={}),
    ):
        result = CliRunner().invoke(
            app, [*prefix, str(image), "--output-dir", str(output), "--quick"]
        )
    assert result.exit_code == 0, result.output
    search.assert_called_once_with(image, output)
    assert "Best preset" in result.output


@pytest.mark.parametrize("subcommand", ["history", "files"])
def test_existing_search_subcommands_remain_reachable(subcommand):
    result = CliRunner().invoke(app, ["search", subcommand, "--help"])
    assert result.exit_code == 0, result.output
    assert subcommand in result.output
