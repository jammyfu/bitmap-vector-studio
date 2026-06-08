from __future__ import annotations

import importlib.util
import json
import logging
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .plugins import PluginManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional watchdog import
# ---------------------------------------------------------------------------
try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer

    _WATCHDOG_AVAILABLE = True
except ImportError:  # pragma: no cover
    _WATCHDOG_AVAILABLE = False
    FileSystemEventHandler = object  # type: ignore[misc,assignment]
    Observer = None  # type: ignore[misc,assignment]


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------

@dataclass
class PluginEvent:
    """Describes a plugin file system event."""

    event_type: str  # 'added', 'modified', 'removed'
    path: Path
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# PluginWatcher
# ---------------------------------------------------------------------------

class _WatchdogHandler(FileSystemEventHandler):  # type: ignore[valid-type, misc]
    """Internal watchdog handler that forwards events to PluginWatcher."""

    def __init__(self, watcher: "PluginWatcher") -> None:
        self.watcher = watcher

    def on_created(self, event: FileSystemEvent) -> None:  # type: ignore[override]
        if not event.is_directory and Path(str(event.src_path)).suffix == ".py":
            self.watcher.on_file_added(Path(str(event.src_path)))

    def on_modified(self, event: FileSystemEvent) -> None:  # type: ignore[override]
        if not event.is_directory and Path(str(event.src_path)).suffix == ".py":
            self.watcher.on_file_changed(Path(str(event.src_path)))

    def on_deleted(self, event: FileSystemEvent) -> None:  # type: ignore[override]
        if not event.is_directory and Path(str(event.src_path)).suffix == ".py":
            self.watcher.on_file_removed(Path(str(event.src_path)))

    def on_moved(self, event: FileSystemEvent) -> None:  # type: ignore[override]
        if not event.is_directory:
            if Path(str(event.src_path)).suffix == ".py":
                self.watcher.on_file_removed(Path(str(event.src_path)))
            if hasattr(event, "dest_path") and Path(str(event.dest_path)).suffix == ".py":
                self.watcher.on_file_added(Path(str(event.dest_path)))


class PluginWatcher:
    """Watch plugin directories and trigger reloads on file changes.

    Uses ``watchdog`` when available; otherwise falls back to a polling
    loop that scans directories every 5 seconds.
    """

    def __init__(self, plugin_dirs: list[Path], manager: PluginManager) -> None:
        """Create a new watcher.

        Parameters
        ----------
        plugin_dirs:
            Directories to monitor for ``.py`` plugin files.
        manager:
            The :class:`PluginManager` instance to reload.
        """
        self.plugin_dirs = [Path(d).resolve() for d in plugin_dirs if Path(d).exists()]
        self.manager = manager
        self._observer: Any = None
        self._polling_timer: threading.Timer | None = None
        self._shutdown = threading.Event()
        self._listeners: list[Callable[[PluginEvent], None]] = []
        self._snapshots: dict[Path, dict[str, float]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_watching(self) -> None:
        """Start the file system monitor.

        Prefers ``watchdog``; falls back to polling if unavailable.
        """
        self._shutdown.clear()
        if _WATCHDOG_AVAILABLE and Observer is not None:
            self._start_watchdog()
        else:
            logger.info("watchdog not available; using polling fallback (5s)")
            self._start_polling()

    def stop_watching(self) -> None:
        """Stop the file system monitor."""
        self._shutdown.set()
        if self._observer is not None:
            self._observer.stop()
            self._observer.join()
            self._observer = None
        if self._polling_timer is not None:
            self._polling_timer.cancel()
            self._polling_timer = None

    def add_listener(self, callback: Callable[[PluginEvent], None]) -> None:
        """Register a callback to be invoked on every plugin event."""
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[PluginEvent], None]) -> None:
        """Unregister a previously added callback."""
        try:
            self._listeners.remove(callback)
        except ValueError:
            pass

    def get_watched_dirs(self) -> list[Path]:
        """Return the list of directories being monitored."""
        return list(self.plugin_dirs)

    # ------------------------------------------------------------------
    # File change callbacks
    # ------------------------------------------------------------------

    def on_file_changed(self, path: Path) -> None:
        """Handle a modified plugin file.

        Detects whether the file is new or existing, then reloads via the
        manager and notifies listeners.
        """
        path = Path(path).resolve()
        event = PluginEvent(event_type="modified", path=path)
        self._notify(event)
        self._reload(path)

    def on_file_added(self, path: Path) -> None:
        """Handle a newly created plugin file."""
        path = Path(path).resolve()
        event = PluginEvent(event_type="added", path=path)
        self._notify(event)
        self._reload(path)

    def on_file_removed(self, path: Path) -> None:
        """Handle a deleted plugin file.

        Attempts to determine the plugin name from the file stem and
        safely unload it.
        """
        path = Path(path).resolve()
        event = PluginEvent(event_type="removed", path=path)
        self._notify(event)
        name = path.stem
        SafePluginReloader(self.manager).unload_plugin_safely(name)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _notify(self, event: PluginEvent) -> None:
        """Invoke all registered listeners."""
        for listener in self._listeners:
            try:
                listener(event)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Plugin event listener failed: %s", exc)

    def _reload(self, path: Path) -> None:
        """Attempt a safe reload of the plugin at *path*."""
        reloader = SafePluginReloader(self.manager)
        ok = reloader.reload_plugin(path)
        if not ok:
            logger.warning("Safe reload failed for %s; old version retained.", path)

    def _start_watchdog(self) -> None:
        """Start the native watchdog observer."""
        self._observer = Observer()
        handler = _WatchdogHandler(self)
        for directory in self.plugin_dirs:
            self._observer.schedule(handler, str(directory), recursive=False)
        self._observer.start()
        logger.info("Watchdog observer started for %d directories", len(self.plugin_dirs))

    def _start_polling(self) -> None:
        """Start the 5-second polling fallback."""
        self._take_snapshots()

        def _tick() -> None:
            if self._shutdown.is_set():
                return
            self._poll_once()
            self._polling_timer = threading.Timer(5.0, _tick)
            self._polling_timer.daemon = True
            self._polling_timer.start()

        _tick()

    def _take_snapshots(self) -> None:
        """Record current mtimes for all ``.py`` files in watched dirs."""
        with self._lock:
            for directory in self.plugin_dirs:
                snap: dict[str, float] = {}
                for py_file in directory.glob("*.py"):
                    if py_file.name.startswith("_"):
                        continue
                    try:
                        snap[py_file.name] = py_file.stat().st_mtime
                    except OSError:
                        continue
                self._snapshots[directory] = snap

    def _poll_once(self) -> None:
        """Compare current directory state with the last snapshot."""
        with self._lock:
            old_snapshots = dict(self._snapshots)
        new_snapshots: dict[Path, dict[str, float]] = {}

        for directory in self.plugin_dirs:
            old = old_snapshots.get(directory, {})
            new: dict[str, float] = {}
            current_files: set[str] = set()
            for py_file in directory.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue
                try:
                    mtime = py_file.stat().st_mtime
                except OSError:
                    continue
                new[py_file.name] = mtime
                current_files.add(py_file.name)
                if py_file.name not in old:
                    self.on_file_added(py_file)
                elif old[py_file.name] != mtime:
                    self.on_file_changed(py_file)
            # Detect deletions
            for name in old:
                if name not in current_files:
                    self.on_file_removed(directory / name)
            new_snapshots[directory] = new

        with self._lock:
            self._snapshots = new_snapshots


# ---------------------------------------------------------------------------
# SafePluginReloader
# ---------------------------------------------------------------------------

class SafePluginReloader:
    """Reload a single plugin safely by validating it in a subprocess first.

    If the subprocess successfully imports the plugin file, the manager's
    in-process registry is updated.  On failure the old plugin remains
    active and the error is logged.
    """

    def __init__(self, manager: PluginManager) -> None:
        """Create a reloader bound to *manager*."""
        self.manager = manager

    def reload_plugin(self, path: Path) -> bool:
        """Safely reload the plugin at *path*.

        Steps:
        1. Spawn a fresh Python process that imports *path* and prints
           discovered plugin names as JSON.
        2. If the subprocess succeeds, update the manager registry.
        3. If the subprocess fails, keep the old plugin and log the error.

        Parameters
        ----------
        path:
            Absolute path to the ``.py`` plugin file.

        Returns
        -------
        bool
            ``True`` if the reload succeeded.
        """
        path = Path(path)
        if not path.exists() or path.suffix != ".py":
            logger.warning("Not a valid plugin file: %s", path)
            return False

        # Build a minimal Python script that imports the file and dumps names.
        test_script = (
            "import importlib.util, inspect, json, sys\n"
            f"spec = importlib.util.spec_from_file_location('_test_plugin', {str(path)!r})\n"
            "mod = importlib.util.module_from_spec(spec)\n"
            "sys.modules['_test_plugin'] = mod\n"
            "spec.loader.exec_module(mod)\n"
            "from vector_studio.plugin_interface import Plugin\n"
            "names = [cls.name for _, cls in inspect.getmembers(mod, inspect.isclass)\n"
            "         if issubclass(cls, Plugin) and cls is not Plugin and cls.name]\n"
            "print(json.dumps(names))\n"
        )

        try:
            result = subprocess.run(
                [sys.executable, "-c", test_script],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Subprocess test failed for %s: %s", path, exc)
            return False

        if result.returncode != 0:
            logger.error(
                "Plugin %s failed subprocess validation: %s",
                path,
                result.stderr.strip(),
            )
            return False

        try:
            names = json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            logger.error("Invalid JSON from plugin test subprocess for %s", path)
            return False

        if not names:
            logger.warning("No valid Plugin subclasses found in %s", path)
            return False

        # Subprocess validation passed → update in-process registry.
        try:
            classes = self.manager._load_classes_from_file(path)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load plugin %s in-process: %s", path, exc)
            return False

        for cls in classes:
            if cls.name:
                # Unload old version if present.
                self.unload_plugin_safely(cls.name)
                self.manager.register_plugin(cls)
                logger.info("Reloaded plugin '%s' from %s", cls.name, path)
        return True

    def unload_plugin_safely(self, name: str) -> bool:
        """Safely remove a plugin from the manager.

        Parameters
        ----------
        name:
            Plugin name to remove.

        Returns
        -------
        bool
            ``True`` if the plugin was known and removed.
        """
        if name not in self.manager._plugin_classes:
            return False
        self.manager.disable_plugin(name)
        del self.manager._plugin_classes[name]
        self.manager._instances.pop(name, None)
        logger.info("Unloaded plugin '%s'", name)
        return True
