from __future__ import annotations

import importlib.util
import inspect
import logging
import shutil
import sys
from pathlib import Path
from typing import Any

from .plugin_interface import Plugin

logger = logging.getLogger(__name__)


def _user_plugin_dir() -> Path:
    """Return the user-level plugin directory."""
    directory = Path.home() / ".bitmap_vector_studio" / "plugins"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _project_plugin_dir() -> Path:
    """Return the project-level plugin directory (``./plugins``)."""
    return Path("plugins").resolve()


def _builtin_plugin_dir() -> Path:
    """Return the built-in plugin directory inside the package."""
    return Path(__file__).parent / "builtin_plugins"


class PluginManager:
    """Discover, register, and execute Bitmap Vector Studio plugins.

    The manager scans three locations by default:

    1. Built-in plugins shipped with the package.
    2. User plugins in ``~/.bitmap_vector_studio/plugins/``.
    3. Project plugins in ``./plugins/`` (current working directory).

    Plugins can also be registered manually via :meth:`register_plugin`.
    """

    def __init__(self, plugin_dirs: list[Path] | None = None) -> None:
        """Create a new manager.

        Parameters
        ----------
        plugin_dirs:
            Extra directories to scan.  The default system directories are
            always scanned in addition to any directories supplied here.
        """
        self._plugin_classes: dict[str, type[Plugin]] = {}
        self._enabled: set[str] = set()
        self._plugin_dirs = plugin_dirs or []
        self._instances: dict[str, Plugin] = {}

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover_plugins(self) -> list[type[Plugin]]:
        """Scan all plugin directories and return discovered subclasses.

        Broken plugins (syntax errors, import failures, etc.) are logged
        and skipped so that a single bad file cannot crash the system.

        Returns
        -------
        list[type[Plugin]]
            List of unique :class:`Plugin` subclasses found.
        """
        discovered: list[type[Plugin]] = []
        seen: set[type[Plugin]] = set()

        dirs = [
            _builtin_plugin_dir(),
            _user_plugin_dir(),
            _project_plugin_dir(),
            *self._plugin_dirs,
        ]

        for directory in dirs:
            if not directory.exists():
                continue
            for py_file in directory.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue
                try:
                    classes = self._load_classes_from_file(py_file)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Failed to load plugin %s: %s", py_file, exc)
                    continue
                for cls in classes:
                    if cls not in seen:
                        seen.add(cls)
                        discovered.append(cls)
                        # Auto-enable newly discovered plugins that are not
                        # already known.
                        if cls.name and cls.name not in self._plugin_classes:
                            self._enabled.add(cls.name)
        return discovered

    @staticmethod
    def _load_classes_from_file(path: Path) -> list[type[Plugin]]:
        """Dynamically import *path* and return all concrete Plugin subclasses."""
        module_name = f"_vector_studio_plugin_{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot create module spec for {path}")

        module = importlib.util.module_from_spec(spec)
        # Keep the module in sys.modules so that relative imports inside the
        # plugin do not break.
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        classes: list[type[Plugin]] = []
        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, Plugin) and obj is not Plugin and obj.name:
                classes.append(obj)
        return classes

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_plugin(self, plugin_class: type[Plugin]) -> None:
        """Manually register a plugin class.

        Parameters
        ----------
        plugin_class:
            A concrete subclass of :class:`Plugin`.

        Raises
        ------
        ValueError
            If *plugin_class* does not define a ``name``.
        """
        if not plugin_class.name:
            raise ValueError("Plugin class must define a 'name' attribute.")
        self._plugin_classes[plugin_class.name] = plugin_class
        self._enabled.add(plugin_class.name)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def enable_plugin(self, name: str) -> None:
        """Enable a plugin by name.

        Raises
        ------
        KeyError
            If the plugin is not known to the manager.
        """
        if name not in self._plugin_classes:
            raise KeyError(f"Unknown plugin: {name}")
        self._enabled.add(name)

    def disable_plugin(self, name: str) -> None:
        """Disable a plugin by name.

        Raises
        ------
        KeyError
            If the plugin is not known to the manager.
        """
        if name not in self._plugin_classes:
            raise KeyError(f"Unknown plugin: {name}")
        self._enabled.discard(name)

    def is_enabled(self, name: str) -> bool:
        """Return ``True`` if the named plugin is enabled."""
        return name in self._enabled

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_plugins(self, hook: str | None = None) -> list[Plugin]:
        """Return enabled plugin instances, optionally filtered by hook.

        Parameters
        ----------
        hook:
            If given, only return plugins that override the named hook
            (one of ``"preprocess"``, ``"postprocess"``, ``"on_convert_complete"``).

        Returns
        -------
        list[Plugin]
            Fresh instances of each enabled plugin.
        """
        instances: list[Plugin] = []
        for name in sorted(self._enabled):
            cls = self._plugin_classes.get(name)
            if cls is None:
                continue
            # Cache a single instance per name for consistency within a run.
            if name not in self._instances:
                self._instances[name] = cls()
            inst = self._instances[name]
            if hook is None or self._has_hook(inst, hook):
                instances.append(inst)
        return instances

    @staticmethod
    def _has_hook(instance: Plugin, hook: str) -> bool:
        """Check whether *instance* actually overrides *hook*."""
        method = getattr(type(instance), hook, None)
        if method is None:
            return False
        # Compare against the base implementation.
        base_method = getattr(Plugin, hook, None)
        return method is not base_method

    def list_plugins(self) -> list[dict[str, Any]]:
        """Return metadata for every known plugin.

        Returns
        -------
        list[dict[str, Any]]
            Each dict contains ``name``, ``version``, ``description``,
            ``author``, ``enabled``, and ``hooks``.
        """
        results: list[dict[str, Any]] = []
        for name, cls in sorted(self._plugin_classes.items()):
            inst = cls()
            hooks = []
            for hook in ("preprocess", "postprocess", "on_convert_complete"):
                if self._has_hook(inst, hook):
                    hooks.append(hook)
            results.append(
                {
                    "name": cls.name,
                    "version": cls.version,
                    "description": cls.description,
                    "author": cls.author,
                    "enabled": name in self._enabled,
                    "hooks": hooks,
                }
            )
        return results

    # ------------------------------------------------------------------
    # Execution helpers
    # ------------------------------------------------------------------

    def run_preprocess(self, image: Any, options: dict[str, Any]) -> Any:
        """Run all enabled ``preprocess`` hooks sequentially.

        Parameters
        ----------
        image:
            A PIL ``Image.Image`` instance.
        options:
            Options dict forwarded to each plugin.

        Returns
        -------
        Image.Image
            The image after all plugins have processed it.
        """
        for plugin in self.get_plugins(hook="preprocess"):
            try:
                image = plugin.preprocess(image, options)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Plugin %s preprocess hook failed: %s", plugin.name, exc)
        return image

    def run_postprocess(self, svg_path: Path, options: dict[str, Any]) -> Path:
        """Run all enabled ``postprocess`` hooks sequentially.

        Parameters
        ----------
        svg_path:
            Path to the SVG file.
        options:
            Options dict forwarded to each plugin.

        Returns
        -------
        Path
            The (possibly updated) SVG path.
        """
        for plugin in self.get_plugins(hook="postprocess"):
            try:
                svg_path = plugin.postprocess(svg_path, options)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Plugin %s postprocess hook failed: %s", plugin.name, exc)
        return svg_path

    def run_on_complete(self, result: Any, options: dict[str, Any]) -> None:
        """Run all enabled ``on_convert_complete`` hooks.

        Parameters
        ----------
        result:
            A :class:`~vector_studio.models.TraceResult` instance.
        options:
            Options dict forwarded to each plugin.
        """
        for plugin in self.get_plugins(hook="on_convert_complete"):
            try:
                plugin.on_convert_complete(result, options)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Plugin %s on_complete hook failed: %s", plugin.name, exc)

    # ------------------------------------------------------------------
    # Installation
    # ------------------------------------------------------------------

    def install_plugin(self, source_path: Path) -> Path:
        """Copy a plugin file into the user plugin directory.

        Parameters
        ----------
        source_path:
            Path to the ``.py`` file to install.

        Returns
        -------
        Path
            The destination path inside the user plugin directory.

        Raises
        ------
        FileNotFoundError
            If *source_path* does not exist.
        ValueError
            If *source_path* is not a ``.py`` file.
        """
        source_path = Path(source_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Plugin file not found: {source_path}")
        if source_path.suffix != ".py":
            raise ValueError("Plugin file must be a .py file")
        dest_dir = _user_plugin_dir()
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / source_path.name
        shutil.copy2(source_path, dest)
        return dest
