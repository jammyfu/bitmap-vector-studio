from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _config_dir() -> Path:
    """Return the user configuration directory."""
    directory = Path.home() / ".bitmap_vector_studio"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _default_config_path() -> Path:
    """Return the default configuration file path.

    Prefers ``config.yaml`` when PyYAML is available, otherwise ``config.json``.
    """
    yaml_path = _config_dir() / "config.yaml"
    json_path = _config_dir() / "config.json"
    if yaml_path.exists():
        return yaml_path
    if json_path.exists():
        return json_path
    # Default to yaml for new files, but we will fall back to json if yaml
    # cannot be written.
    return yaml_path


def _has_yaml() -> bool:
    """Return ``True`` if the ``yaml`` module is installed."""
    try:
        import yaml  # noqa: F401
        return True
    except ImportError:
        return False


def _load_yaml(path: Path) -> dict[str, Any]:
    import yaml

    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        return {}
    return data


def _save_yaml(path: Path, data: dict[str, Any]) -> None:
    import yaml

    with path.open("w", encoding="utf-8") as fh:
        yaml.dump(data, fh, default_flow_style=False, sort_keys=True, allow_unicode=True)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        return {}
    return data


def _save_json(path: Path, data: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")


@dataclass
class Config:
    """Bitmap Vector Studio user configuration.

    Values stored here act as defaults for the CLI and can be overridden
    by explicit command-line arguments.
    """

    default_preset: str = "poster"
    default_output_dir: Path | None = None
    default_optimize_level: str = "basic"
    smart_remove_bg: bool = False
    enhance: str | None = None
    export_pdf: bool = False
    export_png: bool = False
    editor_preference: str | None = None
    max_workers: int = 4
    plugin_dirs: list[str] = field(default_factory=list)
    enabled_plugins: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the configuration to a plain dictionary.

        ``Path`` objects are converted to strings.
        """
        data = asdict(self)
        if data.get("default_output_dir") is not None:
            data["default_output_dir"] = str(data["default_output_dir"])
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Reconstruct a :class:`Config` from a plain dictionary.

        Unknown keys are ignored so that older code can load newer configs
        without crashing.
        """
        known = {f.name for f in cls.__dataclass_fields__.values()}
        clean: dict[str, Any] = {}
        for key, value in data.items():
            if key not in known:
                continue
            if key == "default_output_dir" and value is not None:
                value = Path(value)
            clean[key] = value
        return cls(**clean)

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        """Load configuration from disk.

        Parameters
        ----------
        path:
            Explicit file path.  When ``None`` the default location is used
            (``~/.bitmap_vector_studio/config.yaml`` or ``config.json``).

        Returns
        -------
        Config
            A populated configuration object.  If the file does not exist or
            is unreadable, default values are returned.
        """
        path = path or _default_config_path()
        if not path.exists():
            return cls()

        try:
            if path.suffix in {".yaml", ".yml"} and _has_yaml():
                data = _load_yaml(path)
            else:
                data = _load_json(path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load config from %s: %s", path, exc)
            return cls()

        return cls.from_dict(data)

    def save(self, path: Path | None = None) -> None:
        """Persist configuration to disk.

        Parameters
        ----------
        path:
            Explicit file path.  When ``None`` the default location is used.
            YAML is preferred when PyYAML is installed; otherwise JSON is used.
        """
        path = path or _default_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self.to_dict()

        if path.suffix in {".yaml", ".yml"} and _has_yaml():
            _save_yaml(path, data)
        else:
            # Fall back to JSON if yaml is unavailable or extension is json.
            if path.suffix in {".yaml", ".yml"}:
                path = path.with_suffix(".json")
            _save_json(path, data)

    def merge_with_options(self, **kwargs: Any) -> dict[str, Any]:
        """Merge stored defaults with explicit keyword overrides.

        Command-line values (anything that is not ``None``) take precedence
        over the configuration file values.

        Returns
        -------
        dict[str, Any]
            A flat dictionary suitable for passing as ``**kwargs`` to
            :func:`~vector_studio.tracer.trace_image`.
        """
        defaults = self.to_dict()
        merged: dict[str, Any] = {}

        # Mapping from config keys to trace_image parameter names.
        key_map = {
            "default_preset": "preset",
            "default_output_dir": "output_dir",
            "default_optimize_level": "optimize_level",
            "smart_remove_bg": "smart_remove_bg",
            "enhance": "enhance",
            "export_pdf": "export_pdf",
            "export_png": "export_png",
            "editor_preference": "editor",
            "max_workers": "workers",
        }

        for cfg_key, param_key in key_map.items():
            merged[param_key] = defaults.get(cfg_key)

        # Override with explicit kwargs (non-None values win).
        for key, value in kwargs.items():
            if value is not None:
                merged[key] = value

        return merged

    def validate(self) -> list[str]:
        """Validate the current configuration values.

        Returns
        -------
        list[str]
            A list of human-readable error messages.  An empty list means the
            configuration is valid.
        """
        errors: list[str] = []
        if self.default_optimize_level not in {"none", "basic", "comprehensive", "aggressive"}:
            errors.append(
                f"default_optimize_level must be one of: none, basic, comprehensive, aggressive. "
                f"Got: {self.default_optimize_level}"
            )
        if self.max_workers < 1:
            errors.append(f"max_workers must be >= 1. Got: {self.max_workers}")
        if self.default_output_dir is not None and not isinstance(self.default_output_dir, Path):
            errors.append(f"default_output_dir must be a Path or None. Got: {type(self.default_output_dir)}")
        return errors
