from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vector_studio.plugin_hotreload import (
    PluginEvent,
    PluginWatcher,
    SafePluginReloader,
)
from vector_studio.plugins import PluginManager


class TestPluginWatcherPolling:
    def test_polling_detects_added_file(self, tmp_path):
        manager = PluginManager(plugin_dirs=[tmp_path])
        watcher = PluginWatcher([tmp_path], manager)
        events: list[PluginEvent] = []
        watcher.add_listener(events.append)
        watcher.start_watching()
        try:
            # Write a new plugin file
            plugin_file = tmp_path / "new_plugin.py"
            plugin_file.write_text(
                "from vector_studio.plugin_interface import Plugin\n"
                "class NewPlugin(Plugin):\n"
                "    name = 'new_plugin'\n"
            )
            time.sleep(6.0)
            assert any(e.event_type == "added" for e in events)
        finally:
            watcher.stop_watching()

    def test_polling_detects_modified_file(self, tmp_path):
        plugin_file = tmp_path / "mod_plugin.py"
        plugin_file.write_text(
            "from vector_studio.plugin_interface import Plugin\n"
            "class ModPlugin(Plugin):\n"
            "    name = 'mod_plugin'\n"
        )
        manager = PluginManager(plugin_dirs=[tmp_path])
        watcher = PluginWatcher([tmp_path], manager)
        events: list[PluginEvent] = []
        watcher.add_listener(events.append)
        watcher.start_watching()
        try:
            time.sleep(1.0)
            plugin_file.write_text(
                "from vector_studio.plugin_interface import Plugin\n"
                "class ModPlugin(Plugin):\n"
                "    name = 'mod_plugin'\n"
                "    version = '2.0'\n"
            )
            time.sleep(6.0)
            assert any(e.event_type == "modified" for e in events)
        finally:
            watcher.stop_watching()

    def test_polling_detects_removed_file(self, tmp_path):
        plugin_file = tmp_path / "del_plugin.py"
        plugin_file.write_text(
            "from vector_studio.plugin_interface import Plugin\n"
            "class DelPlugin(Plugin):\n"
            "    name = 'del_plugin'\n"
        )
        manager = PluginManager(plugin_dirs=[tmp_path])
        watcher = PluginWatcher([tmp_path], manager)
        events: list[PluginEvent] = []
        watcher.add_listener(events.append)
        watcher.start_watching()
        try:
            time.sleep(1.0)
            plugin_file.unlink()
            time.sleep(6.0)
            assert any(e.event_type == "removed" for e in events)
        finally:
            watcher.stop_watching()

    def test_get_watched_dirs(self, tmp_path):
        manager = PluginManager()
        watcher = PluginWatcher([tmp_path], manager)
        dirs = watcher.get_watched_dirs()
        assert len(dirs) == 1
        assert dirs[0] == tmp_path.resolve()

    def test_stop_watching_cancels_timer(self, tmp_path):
        manager = PluginManager()
        watcher = PluginWatcher([tmp_path], manager)
        with patch("vector_studio.plugin_hotreload._WATCHDOG_AVAILABLE", False):
            watcher.start_watching()
            assert watcher._polling_timer is not None
            watcher.stop_watching()
            assert watcher._polling_timer is None


class TestSafePluginReloader:
    def test_reload_valid_plugin(self, tmp_path):
        plugin_file = tmp_path / "good_plugin.py"
        plugin_file.write_text(
            "from vector_studio.plugin_interface import Plugin\n"
            "class GoodPlugin(Plugin):\n"
            "    name = 'good_plugin'\n"
            "    version = '1.0.0'\n"
        )
        manager = PluginManager()
        reloader = SafePluginReloader(manager)
        ok = reloader.reload_plugin(plugin_file)
        assert ok is True
        assert "good_plugin" in manager._plugin_classes

    def test_reload_invalid_plugin_returns_false(self, tmp_path):
        bad_file = tmp_path / "bad.py"
        bad_file.write_text("this is not valid python !!!")
        manager = PluginManager()
        reloader = SafePluginReloader(manager)
        ok = reloader.reload_plugin(bad_file)
        assert ok is False

    def test_reload_nonexistent_returns_false(self, tmp_path):
        manager = PluginManager()
        reloader = SafePluginReloader(manager)
        ok = reloader.reload_plugin(tmp_path / "missing.py")
        assert ok is False

    def test_unload_plugin_safely(self):
        class FakePlugin:
            name = "fake"

        manager = PluginManager()
        manager._plugin_classes["fake"] = FakePlugin  # type: ignore[assignment]
        manager._enabled.add("fake")
        reloader = SafePluginReloader(manager)
        assert reloader.unload_plugin_safely("fake") is True
        assert "fake" not in manager._plugin_classes
        assert reloader.unload_plugin_safely("fake") is False

    def test_reload_replaces_old_version(self, tmp_path):
        plugin_file = tmp_path / "replace.py"
        plugin_file.write_text(
            "from vector_studio.plugin_interface import Plugin\n"
            "class ReplacePlugin(Plugin):\n"
            "    name = 'replace_plugin'\n"
            "    version = '1.0'\n"
        )
        manager = PluginManager()
        reloader = SafePluginReloader(manager)
        reloader.reload_plugin(plugin_file)
        # Update file
        time.sleep(0.1)
        plugin_file.write_text(
            "from vector_studio.plugin_interface import Plugin\n"
            "class ReplacePlugin(Plugin):\n"
            "    name = 'replace_plugin'\n"
            "    version = '2.0'\n"
        )
        # Clear Python bytecode cache to force recompilation.
        pycache = tmp_path / "__pycache__"
        if pycache.exists():
            for pyc in pycache.glob("*.pyc"):
                pyc.unlink()
        time.sleep(0.1)
        reloader.reload_plugin(plugin_file)
        cls = manager._plugin_classes.get("replace_plugin")
        assert cls is not None
        assert cls.version == "2.0"


class TestPluginEvent:
    def test_event_dataclass(self):
        event = PluginEvent(event_type="added", path=Path("/tmp/p.py"))
        assert event.event_type == "added"
        assert event.path == Path("/tmp/p.py")
        assert event.timestamp is not None

    def test_listener_exceptions_ignored(self, tmp_path):
        manager = PluginManager()
        watcher = PluginWatcher([tmp_path], manager)

        def bad_listener(event: PluginEvent) -> None:
            raise RuntimeError("boom")

        watcher.add_listener(bad_listener)
        # Should not raise
        watcher._notify(PluginEvent("added", tmp_path / "x.py"))

    def test_remove_listener(self, tmp_path):
        manager = PluginManager()
        watcher = PluginWatcher([tmp_path], manager)
        called = False

        def listener(event: PluginEvent) -> None:
            nonlocal called
            called = True

        watcher.add_listener(listener)
        watcher.remove_listener(listener)
        watcher._notify(PluginEvent("added", tmp_path / "x.py"))
        assert not called

    def test_on_file_added_calls_reload(self, tmp_path):
        manager = PluginManager()
        watcher = PluginWatcher([tmp_path], manager)
        with patch.object(watcher, "_reload") as mock_reload:
            watcher.on_file_added(tmp_path / "x.py")
            mock_reload.assert_called_once()

    def test_on_file_removed_calls_unload(self, tmp_path):
        manager = PluginManager()
        watcher = PluginWatcher([tmp_path], manager)
        with patch.object(SafePluginReloader, "unload_plugin_safely") as mock_unload:
            watcher.on_file_removed(tmp_path / "x.py")
            mock_unload.assert_called_once_with("x")
