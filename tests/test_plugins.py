from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from vector_studio.builtin_plugins.resize_plugin import ResizePlugin
from vector_studio.builtin_plugins.watermark_plugin import WatermarkPlugin
from vector_studio.models import TraceResult
from vector_studio.plugin_interface import Plugin
from vector_studio.plugins import PluginManager


class TestPluginBaseClass:
    def test_preprocess_returns_image_unchanged(self):
        img = Image.new("RGB", (10, 10), color=(255, 0, 0))
        plugin = Plugin()
        result = plugin.preprocess(img, {})
        assert result == img

    def test_postprocess_returns_path_unchanged(self, tmp_path):
        svg = tmp_path / "test.svg"
        svg.write_text("<svg></svg>")
        plugin = Plugin()
        result = plugin.postprocess(svg, {})
        assert result == svg

    def test_on_complete_is_noop(self):
        result = MagicMock()
        plugin = Plugin()
        plugin.on_convert_complete(result, {})


class TestPluginManagerDiscovery:
    def test_discovers_builtin_plugins(self):
        manager = PluginManager()
        discovered = manager.discover_plugins()
        names = {cls.name for cls in discovered}
        assert "watermark" in names
        assert "resize" in names

    def test_discovers_from_custom_dir(self, tmp_path):
        plugin_file = tmp_path / "my_plugin.py"
        plugin_file.write_text(
            "from vector_studio.plugin_interface import Plugin\n"
            "class MyPlugin(Plugin):\n"
            "    name = 'my_plugin'\n"
            "    version = '0.1.0'\n"
            "    def preprocess(self, image, options):\n"
            "        return image\n"
        )
        manager = PluginManager(plugin_dirs=[tmp_path])
        discovered = manager.discover_plugins()
        names = {cls.name for cls in discovered}
        assert "my_plugin" in names

    def test_skips_broken_plugin_gracefully(self, tmp_path):
        bad_plugin = tmp_path / "bad_plugin.py"
        bad_plugin.write_text("this is not valid python !!!")
        manager = PluginManager(plugin_dirs=[tmp_path])
        discovered = manager.discover_plugins()
        names = {cls.name for cls in discovered}
        assert "bad_plugin" not in names


class TestPluginManagerRegistration:
    def test_register_plugin_requires_name(self):
        class NoName(Plugin):
            pass

        manager = PluginManager()
        with pytest.raises(ValueError, match="name"):
            manager.register_plugin(NoName)

    def test_register_and_retrieve(self):
        class TestPlugin(Plugin):
            name = "test_plugin"
            version = "1.0.0"

        manager = PluginManager()
        manager.register_plugin(TestPlugin)
        plugins = manager.get_plugins()
        assert len(plugins) == 1
        assert plugins[0].name == "test_plugin"


class TestPluginManagerEnableDisable:
    def test_enable_disable(self):
        class TestPlugin(Plugin):
            name = "test_plugin"

        manager = PluginManager()
        manager.register_plugin(TestPlugin)
        assert manager.is_enabled("test_plugin")
        manager.disable_plugin("test_plugin")
        assert not manager.is_enabled("test_plugin")
        manager.enable_plugin("test_plugin")
        assert manager.is_enabled("test_plugin")

    def test_disable_unknown_raises_keyerror(self):
        manager = PluginManager()
        with pytest.raises(KeyError, match="Unknown plugin"):
            manager.disable_plugin("nonexistent")


class TestPluginManagerListPlugins:
    def test_list_plugins_metadata(self):
        class TestPlugin(Plugin):
            name = "test_plugin"
            version = "1.0.0"
            description = "A test plugin"
            author = "Tester"

            def preprocess(self, image, options):
                return image

        manager = PluginManager()
        manager.register_plugin(TestPlugin)
        info = manager.list_plugins()
        assert len(info) == 1
        assert info[0]["name"] == "test_plugin"
        assert info[0]["version"] == "1.0.0"
        assert info[0]["description"] == "A test plugin"
        assert info[0]["author"] == "Tester"
        assert info[0]["enabled"] is True
        assert "preprocess" in info[0]["hooks"]


class TestPluginManagerExecution:
    def test_run_preprocess_chain(self):
        class FlipPlugin(Plugin):
            name = "flip"

            def preprocess(self, image, options):
                return image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

        manager = PluginManager()
        manager.register_plugin(FlipPlugin)
        img = Image.new("RGB", (10, 10), color=(255, 0, 0))
        result = manager.run_preprocess(img, {})
        assert isinstance(result, Image.Image)
        assert result.size == (10, 10)

    def test_run_postprocess_chain(self, tmp_path):
        class TouchPlugin(Plugin):
            name = "touch"

            def postprocess(self, svg_path, options):
                marker = svg_path.with_suffix(".marker")
                marker.write_text("touched")
                return svg_path

        manager = PluginManager()
        manager.register_plugin(TouchPlugin)
        svg = tmp_path / "test.svg"
        svg.write_text("<svg></svg>")
        result = manager.run_postprocess(svg, {})
        assert result == svg
        assert (tmp_path / "test.marker").exists()

    def test_run_on_complete_chain(self):
        class RecordPlugin(Plugin):
            name = "record"
            calls: list[Any] = []

            def on_convert_complete(self, result, options):
                self.calls.append(result)

        manager = PluginManager()
        manager.register_plugin(RecordPlugin)
        mock_result = MagicMock()
        manager.run_on_complete(mock_result, {})
        assert len(RecordPlugin.calls) == 1

    def test_run_hooks_ignore_exceptions(self):
        class BadPlugin(Plugin):
            name = "bad"

            def preprocess(self, image, options):
                raise RuntimeError("boom")

        manager = PluginManager()
        manager.register_plugin(BadPlugin)
        img = Image.new("RGB", (10, 10))
        with patch("vector_studio.plugins.logger"):
            result = manager.run_preprocess(img, {})
        assert result == img

    def test_get_plugins_filtered_by_hook(self):
        class PrePlugin(Plugin):
            name = "pre"

            def preprocess(self, image, options):
                return image

        class PostPlugin(Plugin):
            name = "post"

            def postprocess(self, svg_path, options):
                return svg_path

        manager = PluginManager()
        manager.register_plugin(PrePlugin)
        manager.register_plugin(PostPlugin)
        pre = manager.get_plugins(hook="preprocess")
        assert len(pre) == 1
        assert pre[0].name == "pre"
        post = manager.get_plugins(hook="postprocess")
        assert len(post) == 1
        assert post[0].name == "post"


class TestPluginManagerInstall:
    def test_install_plugin(self, tmp_path):
        source = tmp_path / "my_plugin.py"
        source.write_text(
            "from vector_studio.plugin_interface import Plugin\n"
            "class InstalledPlugin(Plugin):\n"
            "    name = 'installed'\n"
        )
        manager = PluginManager()
        user_dir = tmp_path / "user_plugins"
        user_dir.mkdir(parents=True, exist_ok=True)
        with patch("vector_studio.plugins._user_plugin_dir", return_value=user_dir):
            dest = manager.install_plugin(source)
        assert dest.exists()
        assert dest.name == "my_plugin.py"

    def test_install_non_py_raises(self, tmp_path):
        source = tmp_path / "readme.txt"
        source.write_text("hello")
        manager = PluginManager()
        with pytest.raises(ValueError, match=".py"):
            manager.install_plugin(source)


class TestBuiltinPlugins:
    def test_watermark_plugin_postprocess(self, tmp_path):
        svg = tmp_path / "test.svg"
        svg.write_text('<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"></svg>')
        plugin = WatermarkPlugin()
        result = plugin.postprocess(svg, {"watermark_text": "Hello"})
        assert result == svg
        content = svg.read_text()
        assert "Hello" in content
        assert "text" in content

    def test_resize_plugin_postprocess(self, tmp_path):
        svg = tmp_path / "test.svg"
        svg.write_text(
            '<svg width="100" height="100" viewBox="0 0 100 100" '
            'xmlns="http://www.w3.org/2000/svg"></svg>'
        )
        plugin = ResizePlugin()
        result = plugin.postprocess(svg, {"resize_scale": 2.0})
        assert result == svg
        content = svg.read_text()
        assert 'width="200.0"' in content
        assert 'height="200.0"' in content
        assert 'viewBox="0.0 0.0 200.0 200.0"' in content

    def test_resize_plugin_no_scale_returns_unchanged(self, tmp_path):
        svg = tmp_path / "test.svg"
        original = '<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg"></svg>'
        svg.write_text(original)
        plugin = ResizePlugin()
        result = plugin.postprocess(svg, {})
        assert result == svg
        assert svg.read_text() == original
