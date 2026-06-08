import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from vector_studio.cli import app
from vector_studio.market import (
    GitHubGistBackend,
    GitHubRepoBackend,
    MarketBackend,
    MultiBackend,
    PresetMarket,
    _load_ratings,
    _save_ratings,
)
from vector_studio.models import TraceOptions

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _isolated_stores(monkeypatch, tmp_path):
    """Redirect user presets and market ratings into a temporary directory."""
    from vector_studio import preset_manager as pm

    store = tmp_path / "presets.json"
    monkeypatch.setattr(pm, "_user_presets_file", lambda: store)
    store.unlink(missing_ok=True)

    ratings = tmp_path / "ratings.json"
    monkeypatch.setattr("vector_studio.market._ratings_file", lambda: ratings)
    ratings.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# MarketBackend & MultiBackend
# ---------------------------------------------------------------------------

class TestMarketBackend:
    def test_market_backend_is_abstract(self):
        """Instantiating the abstract base class must raise TypeError."""
        with pytest.raises(TypeError):
            MarketBackend()

    def test_multi_backend_list_presets(self):
        """MultiBackend aggregates list_presets from all sub-backends."""
        b1 = MagicMock(spec=MarketBackend)
        b1.list_presets.return_value = [{"id": "a", "name": "preset_a"}]
        b2 = MagicMock(spec=MarketBackend)
        b2.list_presets.return_value = [{"id": "b", "name": "preset_b"}]

        multi = MultiBackend([b1, b2])
        result = multi.list_presets()
        assert len(result) == 2
        assert result[0]["id"] == "a"
        assert result[1]["id"] == "b"

    def test_multi_backend_search_presets_dedup(self):
        """MultiBackend deduplicates search results by preset ID."""
        b1 = MagicMock(spec=MarketBackend)
        b1.search_presets.return_value = [{"id": "a", "name": "preset_a"}]
        b2 = MagicMock(spec=MarketBackend)
        b2.search_presets.return_value = [{"id": "a", "name": "preset_a"}]

        multi = MultiBackend([b1, b2])
        result = multi.search_presets("test")
        assert len(result) == 1

    def test_multi_backend_download_preset_fallback(self):
        """MultiBackend tries each backend until the preset is found."""
        b1 = MagicMock(spec=MarketBackend)
        b1.download_preset.side_effect = ValueError("not found")
        b2 = MagicMock(spec=MarketBackend)
        b2.download_preset.return_value = {"id": "x", "name": "found"}

        multi = MultiBackend([b1, b2])
        result = multi.download_preset("x")
        assert result["name"] == "found"

    def test_multi_backend_upload_preset_fallback(self):
        """MultiBackend tries each backend until upload succeeds."""
        b1 = MagicMock(spec=MarketBackend)
        b1.upload_preset.side_effect = RuntimeError("fail")
        b2 = MagicMock(spec=MarketBackend)
        b2.upload_preset.return_value = "new-id"

        multi = MultiBackend([b1, b2])
        result = multi.upload_preset({"name": "test"}, "token")
        assert result == "new-id"


# ---------------------------------------------------------------------------
# GitHubGistBackend
# ---------------------------------------------------------------------------

class TestGitHubGistBackend:
    def test_gist_backend_list_presets_from_description(self):
        """Gist description parsed as JSON yields preset metadata."""
        gist_data = [
            {
                "id": "gist-123",
                "description": json.dumps(
                    {
                        "id": "gist-123",
                        "name": "logo_preset",
                        "display_name": "Logo Preset",
                        "author": "test",
                        "version": "1.0.0",
                        "tags": ["logo"],
                        "downloads": 5,
                        "rating": 4.0,
                        "options": {},
                        "created_at": "2024-01-01",
                    }
                ),
                "files": {},
            }
        ]

        backend = GitHubGistBackend(username="testuser")
        with patch("vector_studio.market._http_json", return_value=gist_data):
            presets = backend.list_presets()

        assert len(presets) == 1
        assert presets[0]["name"] == "logo_preset"
        assert presets[0]["display_name"] == "Logo Preset"

    def test_gist_backend_download_preset_from_file(self):
        """Downloading a preset fetches the JSON file inside the gist."""
        gist_data = {
            "id": "gist-456",
            "description": "My Preset",
            "files": {
                "data.json": {
                    "raw_url": "https://gist.githubusercontent.com/test/gist-456/raw/data.json"
                }
            },
        }
        raw_data = {
            "id": "gist-456",
            "name": "my_preset",
            "display_name": "My Preset",
            "options": {"colormode": "binary", "filter_speckle": 8},
        }

        backend = GitHubGistBackend()

        def mock_http(url, **kwargs):
            if "gists/gist-456" in url:
                return gist_data
            return raw_data

        with patch("vector_studio.market._http_json", side_effect=mock_http):
            preset = backend.download_preset("gist-456")

        assert preset["name"] == "my_preset"
        assert preset["options"]["colormode"] == "binary"

    def test_gist_backend_search_presets(self):
        """Search filters presets by name, display_name and tags."""
        gist_data = [
            {
                "id": "gist-789",
                "description": json.dumps(
                    {
                        "id": "gist-789",
                        "name": "photo_preset",
                        "display_name": "Photo Preset",
                        "tags": ["photo"],
                        "options": {},
                    }
                ),
                "files": {},
            }
        ]

        backend = GitHubGistBackend(username="testuser")
        with patch("vector_studio.market._http_json", return_value=gist_data):
            result = backend.search_presets("photo")

        assert len(result) == 1
        assert result[0]["name"] == "photo_preset"


# ---------------------------------------------------------------------------
# GitHubRepoBackend
# ---------------------------------------------------------------------------

class TestGitHubRepoBackend:
    def test_repo_backend_list_presets(self):
        """Repo backend lists only .json files as presets."""
        contents = [
            {"type": "file", "name": "logo.json", "path": "presets/logo.json"},
            {"type": "file", "name": "photo.json", "path": "presets/photo.json"},
            {"type": "dir", "name": "subfolder", "path": "presets/subfolder"},
        ]

        backend = GitHubRepoBackend("owner", "repo", path="presets")
        with patch("vector_studio.market._http_json", return_value=contents):
            presets = backend.list_presets()

        assert len(presets) == 2
        names = {p["name"] for p in presets}
        assert names == {"logo", "photo"}

    def test_repo_backend_download_preset(self):
        """Repo backend downloads raw JSON from raw.githubusercontent.com."""
        raw_data = {
            "id": "presets/scan.json",
            "name": "scan",
            "options": {"colormode": "binary", "filter_speckle": 4},
        }

        backend = GitHubRepoBackend("owner", "repo", path="presets")
        with patch("vector_studio.market._http_json", return_value=raw_data):
            preset = backend.download_preset("presets/scan.json")

        assert preset["name"] == "scan"
        assert preset["options"]["filter_speckle"] == 4


# ---------------------------------------------------------------------------
# PresetMarket
# ---------------------------------------------------------------------------

class TestPresetMarket:
    def test_preset_market_discover_presets(self):
        """discover_presets delegates to the backend."""
        backend = MagicMock(spec=MarketBackend)
        backend.list_presets.return_value = [
            {"id": "p1", "name": "preset1", "rating": 4.5, "downloads": 10},
        ]
        market = PresetMarket(backend=backend)
        presets = market.discover_presets()
        assert len(presets) == 1
        assert presets[0]["id"] == "p1"

    def test_preset_market_install(self):
        """install downloads and saves a preset via preset_manager."""
        backend = MagicMock(spec=MarketBackend)
        backend.download_preset.return_value = {
            "id": "p1",
            "name": "my_preset",
            "options": {
                "colormode": "binary",
                "hierarchical": "stacked",
                "mode": "spline",
                "filter_speckle": 8,
                "color_precision": 4,
                "layer_difference": 16,
                "corner_threshold": 60,
                "length_threshold": 4.0,
                "max_iterations": 10,
                "splice_threshold": 45,
                "path_precision": 3,
            },
        }
        market = PresetMarket(backend=backend)
        local_name = market.install("p1")
        assert local_name == "my_preset"

        from vector_studio import preset_manager as pm

        loaded = pm.load_preset("my_preset")
        assert loaded.colormode == "binary"
        assert loaded.filter_speckle == 8

    def test_preset_market_rate(self):
        """rate stores a local rating persistently."""
        market = PresetMarket(backend=MagicMock(spec=MarketBackend))
        market.rate("preset-1", 5)
        ratings = _load_ratings()
        assert ratings["preset-1"]["rating"] == 5

    def test_preset_market_rate_out_of_range(self):
        """rate rejects values outside 1–5."""
        market = PresetMarket(backend=MagicMock(spec=MarketBackend))
        with pytest.raises(ValueError, match="Rating must be between 1 and 5"):
            market.rate("preset-1", 0)
        with pytest.raises(ValueError, match="Rating must be between 1 and 5"):
            market.rate("preset-1", 6)

    def test_preset_market_get_popular(self):
        """get_popular sorts by effective rating then downloads."""
        backend = MagicMock(spec=MarketBackend)
        backend.list_presets.return_value = [
            {"id": "a", "name": "a", "rating": 3.0, "downloads": 100},
            {"id": "b", "name": "b", "rating": 5.0, "downloads": 50},
            {"id": "c", "name": "c", "rating": 4.0, "downloads": 200},
        ]
        market = PresetMarket(backend=backend)
        popular = market.get_popular(limit=2)
        assert len(popular) == 2
        # Highest rating first
        assert popular[0]["id"] == "b"
        assert popular[1]["id"] == "c"

    def test_preset_market_get_popular_with_local_rating(self):
        """Local ratings override market ratings when sorting."""
        backend = MagicMock(spec=MarketBackend)
        backend.list_presets.return_value = [
            {"id": "x", "name": "x", "rating": 2.0, "downloads": 1000},
        ]
        market = PresetMarket(backend=backend)
        market.rate("x", 5)
        popular = market.get_popular(limit=1)
        assert popular[0]["id"] == "x"

    def test_preset_market_publish(self):
        """publish loads a local preset and uploads it."""
        from vector_studio import preset_manager as pm

        pm.save_preset("local_preset", TraceOptions(colormode="binary"))

        backend = MagicMock(spec=MarketBackend)
        backend.upload_preset.return_value = "market-id-123"
        market = PresetMarket(backend=backend)
        result = market.publish("local_preset", "fake-token")
        assert result == "market-id-123"

        call_args = backend.upload_preset.call_args
        assert call_args[0][0]["name"] == "local_preset"
        assert call_args[0][0]["options"]["colormode"] == "binary"
        assert call_args[0][1] == "fake-token"

    def test_preset_market_publish_includes_description(self):
        """publish preserves the user preset description when available."""
        from vector_studio import preset_manager as pm

        pm.save_preset("desc_preset", TraceOptions(), description="my description")

        backend = MagicMock(spec=MarketBackend)
        backend.upload_preset.return_value = "id"
        market = PresetMarket(backend=backend)
        market.publish("desc_preset", "token")

        uploaded = backend.upload_preset.call_args[0][0]
        assert uploaded["description"] == "my description"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

class TestMarketCLI:
    def test_cli_market_list(self):
        """market list renders a Rich table with preset data."""
        with patch("vector_studio.market.PresetMarket") as mock_market_cls:
            instance = mock_market_cls.return_value
            instance.discover_presets.return_value = [
                {
                    "id": "p1",
                    "name": "preset1",
                    "display_name": "Preset One",
                    "author": "alice",
                    "version": "1.0",
                    "tags": ["logo"],
                    "rating": 4.5,
                    "downloads": 42,
                },
            ]
            result = runner.invoke(app, ["market", "list"])

        assert result.exit_code == 0
        assert "p1" in result.output
        assert "Preset One" in result.output

    def test_cli_market_search(self):
        """market search renders results for the query."""
        with patch("vector_studio.market.PresetMarket") as mock_market_cls:
            instance = mock_market_cls.return_value
            instance.search.return_value = [
                {
                    "id": "p2",
                    "name": "photo_preset",
                    "display_name": "Photo",
                    "author": "bob",
                    "tags": ["photo"],
                },
            ]
            result = runner.invoke(app, ["market", "search", "photo"])

        assert result.exit_code == 0
        assert "p2" in result.output
        assert "Photo" in result.output

    def test_cli_market_install(self):
        """market install calls PresetMarket.install with the correct arguments."""
        with patch("vector_studio.market.PresetMarket") as mock_market_cls:
            instance = mock_market_cls.return_value
            instance.install.return_value = "installed_preset"
            result = runner.invoke(app, ["market", "install", "p3", "--name", "my_name"])

        assert result.exit_code == 0
        assert "Installed preset" in result.output
        instance.install.assert_called_once_with("p3", name="my_name")

    def test_cli_market_publish_no_token(self):
        """market publish exits early when no auth token is provided."""
        env = dict(os.environ)
        env.pop("GITHUB_TOKEN", None)
        with patch.dict(os.environ, env, clear=True):
            result = runner.invoke(app, ["market", "publish", "local_preset"])
        assert result.exit_code == 1
        assert "GitHub token required" in result.output

    def test_cli_market_popular(self):
        """market popular renders a table of top presets."""
        with patch("vector_studio.market.PresetMarket") as mock_market_cls:
            instance = mock_market_cls.return_value
            instance.get_popular.return_value = [
                {
                    "id": "pop1",
                    "name": "popular",
                    "display_name": "Popular",
                    "rating": 5.0,
                    "downloads": 999,
                },
            ]
            result = runner.invoke(app, ["market", "popular"])

        assert result.exit_code == 0
        assert "pop1" in result.output

    def test_cli_market_info(self):
        """market info downloads and displays a single preset."""
        with patch("vector_studio.market.PresetMarket") as mock_market_cls:
            instance = mock_market_cls.return_value
            instance.backend.download_preset.return_value = {
                "id": "info1",
                "name": "info_preset",
                "display_name": "Info Preset",
                "description": "A test preset",
                "author": "tester",
                "version": "1.0.0",
                "tags": ["test"],
                "downloads": 10,
                "rating": 4.0,
                "created_at": "2024-01-01",
            }
            result = runner.invoke(app, ["market", "info", "info1"])

        assert result.exit_code == 0
        assert "Info Preset" in result.output
        assert "A test preset" in result.output

    def test_cli_market_list_empty(self):
        """market list prints a friendly message when no presets are found."""
        with patch("vector_studio.market.PresetMarket") as mock_market_cls:
            instance = mock_market_cls.return_value
            instance.discover_presets.return_value = []
            result = runner.invoke(app, ["market", "list"])

        assert result.exit_code == 0
        assert "No presets found" in result.output

    def test_cli_market_install_failure(self):
        """market install exits with code 1 on failure."""
        with patch("vector_studio.market.PresetMarket") as mock_market_cls:
            instance = mock_market_cls.return_value
            instance.install.side_effect = ValueError("bad preset")
            result = runner.invoke(app, ["market", "install", "bad"])

        assert result.exit_code == 1
        assert "Installation failed" in result.output
