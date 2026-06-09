from __future__ import annotations

from pathlib import Path

import pytest

from vector_studio.plugin_market import PluginMarket, PluginPackage


class TestPluginPackage:
    def test_to_dict_roundtrip(self, tmp_path: Path):
        pkg = PluginPackage(
            package_id="test_pkg",
            name="Test Package",
            version="1.0.0",
            description="A test package",
            author="Tester",
            category="utility",
            tags=["test", "demo"],
            rating=4.5,
            downloads=100,
            dependencies=[],
            min_app_version="3.0.0",
            source_url=None,
            install_path=tmp_path / "plugin.py",
            installed=True,
            enabled=False,
        )
        d = pkg.to_dict()
        assert d["package_id"] == "test_pkg"
        assert d["install_path"] == str(tmp_path / "plugin.py")
        assert d["installed"] is True

        restored = PluginPackage.from_dict(d)
        assert restored.package_id == pkg.package_id
        assert restored.install_path == tmp_path / "plugin.py"


class TestPluginMarket:
    def test_init_creates_directory(self, tmp_path: Path):
        market_dir = tmp_path / "market"
        market = PluginMarket(market_dir=market_dir)
        assert market_dir.exists()
        assert market.index_file.exists() is False  # empty index not saved yet

    def test_publish_and_discover(self, tmp_path: Path):
        market = PluginMarket(market_dir=tmp_path / "market")
        pkg = PluginPackage(
            package_id="pkg_1",
            name="Package One",
            version="1.0.0",
            description="First package",
            author="A",
            category="filter",
            tags=["photo"],
            rating=0.0,
            downloads=10,
            dependencies=[],
            min_app_version="3.0.0",
            source_url=None,
            install_path=None,
            installed=False,
            enabled=False,
        )
        pid = market.publish_plugin(pkg)
        assert pid == "pkg_1"

        results = market.discover_plugins()
        assert len(results) == 1
        assert results[0].package_id == "pkg_1"

    def test_discover_with_query(self, tmp_path: Path):
        market = PluginMarket(market_dir=tmp_path / "market")
        market.publish_plugin(
            PluginPackage(
                package_id="alpha",
                name="Alpha Plugin",
                version="1.0.0",
                description="Alpha description",
                author="A",
                category="filter",
                tags=["tag1"],
                rating=0.0,
                downloads=0,
                dependencies=[],
                min_app_version="3.0.0",
                source_url=None,
                install_path=None,
                installed=False,
                enabled=False,
            )
        )
        market.publish_plugin(
            PluginPackage(
                package_id="beta",
                name="Beta Plugin",
                version="1.0.0",
                description="Beta description",
                author="B",
                category="ai",
                tags=["tag2"],
                rating=0.0,
                downloads=0,
                dependencies=[],
                min_app_version="3.0.0",
                source_url=None,
                install_path=None,
                installed=False,
                enabled=False,
            )
        )

        results = market.discover_plugins(query="alpha")
        assert len(results) == 1
        assert results[0].package_id == "alpha"

        results = market.discover_plugins(query="tag2")
        assert len(results) == 1
        assert results[0].package_id == "beta"

    def test_discover_with_category(self, tmp_path: Path):
        market = PluginMarket(market_dir=tmp_path / "market")
        market.publish_plugin(
            PluginPackage(
                package_id="f1",
                name="Filter One",
                version="1.0.0",
                description="D",
                author="A",
                category="filter",
                tags=[],
                rating=0.0,
                downloads=0,
                dependencies=[],
                min_app_version="3.0.0",
                source_url=None,
                install_path=None,
                installed=False,
                enabled=False,
            )
        )
        market.publish_plugin(
            PluginPackage(
                package_id="a1",
                name="AI One",
                version="1.0.0",
                description="D",
                author="A",
                category="ai",
                tags=[],
                rating=0.0,
                downloads=0,
                dependencies=[],
                min_app_version="3.0.0",
                source_url=None,
                install_path=None,
                installed=False,
                enabled=False,
            )
        )

        results = market.discover_plugins(category="filter")
        assert len(results) == 1
        assert results[0].package_id == "f1"

    def test_rate_plugin(self, tmp_path: Path):
        market = PluginMarket(market_dir=tmp_path / "market")
        market.publish_plugin(
            PluginPackage(
                package_id="r1",
                name="Rateable",
                version="1.0.0",
                description="D",
                author="A",
                category="utility",
                tags=[],
                rating=0.0,
                downloads=0,
                dependencies=[],
                min_app_version="3.0.0",
                source_url=None,
                install_path=None,
                installed=False,
                enabled=False,
            )
        )

        assert market.rate_plugin("r1", "user_a", 5) is True
        assert market.rate_plugin("r1", "user_b", 3) is True
        assert market.rate_plugin("r1", "user_c", 0) is False  # invalid rating

        plugin = market.get_plugin("r1")
        assert plugin is not None
        assert plugin.rating == 4.0  # (5 + 3) / 2

    def test_install_and_uninstall(self, tmp_path: Path):
        market = PluginMarket(market_dir=tmp_path / "market")
        market.publish_plugin(
            PluginPackage(
                package_id="i1",
                name="Installable",
                version="1.0.0",
                description="D",
                author="A",
                category="utility",
                tags=[],
                rating=0.0,
                downloads=0,
                dependencies=[],
                min_app_version="3.0.0",
                source_url=None,
                install_path=None,
                installed=False,
                enabled=False,
            )
        )

        source = tmp_path / "plugin.py"
        source.write_text("# plugin")

        assert market.install_plugin("i1", source) is True
        plugin = market.get_plugin("i1")
        assert plugin is not None
        assert plugin.installed is True
        assert plugin.install_path == source

        assert market.uninstall_plugin("i1") is True
        plugin = market.get_plugin("i1")
        assert plugin is not None
        assert plugin.installed is False
        assert plugin.enabled is False
        assert plugin.install_path is None

    def test_get_categories(self, tmp_path: Path):
        market = PluginMarket(market_dir=tmp_path / "market")
        market.publish_plugin(
            PluginPackage(
                package_id="c1",
                name="C1",
                version="1.0.0",
                description="D",
                author="A",
                category="filter",
                tags=[],
                rating=0.0,
                downloads=0,
                dependencies=[],
                min_app_version="3.0.0",
                source_url=None,
                install_path=None,
                installed=False,
                enabled=False,
            )
        )
        market.publish_plugin(
            PluginPackage(
                package_id="c2",
                name="C2",
                version="1.0.0",
                description="D",
                author="A",
                category="filter",
                tags=[],
                rating=0.0,
                downloads=0,
                dependencies=[],
                min_app_version="3.0.0",
                source_url=None,
                install_path=None,
                installed=False,
                enabled=False,
            )
        )
        market.publish_plugin(
            PluginPackage(
                package_id="c3",
                name="C3",
                version="1.0.0",
                description="D",
                author="A",
                category="ai",
                tags=[],
                rating=0.0,
                downloads=0,
                dependencies=[],
                min_app_version="3.0.0",
                source_url=None,
                install_path=None,
                installed=False,
                enabled=False,
            )
        )

        counts = market.get_categories()
        assert counts["filter"] == 2
        assert counts["ai"] == 1

    def test_sort_by_downloads(self, tmp_path: Path):
        market = PluginMarket(market_dir=tmp_path / "market")
        market.publish_plugin(
            PluginPackage(
                package_id="low",
                name="Low",
                version="1.0.0",
                description="D",
                author="A",
                category="utility",
                tags=[],
                rating=5.0,
                downloads=10,
                dependencies=[],
                min_app_version="3.0.0",
                source_url=None,
                install_path=None,
                installed=False,
                enabled=False,
            )
        )
        market.publish_plugin(
            PluginPackage(
                package_id="high",
                name="High",
                version="1.0.0",
                description="D",
                author="A",
                category="utility",
                tags=[],
                rating=3.0,
                downloads=100,
                dependencies=[],
                min_app_version="3.0.0",
                source_url=None,
                install_path=None,
                installed=False,
                enabled=False,
            )
        )

        results = market.discover_plugins(sort_by="downloads")
        assert results[0].package_id == "high"
        assert results[1].package_id == "low"
