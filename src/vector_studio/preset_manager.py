from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import TraceOptions
from .presets import PRESETS


def _normalize_preset_name(name: str) -> str:
    """Normalize a preset name to lowercase with underscores.

    Spaces and hyphens are replaced with underscores so that
    ``"Pixel Art"``, ``"pixel-art"`` and ``"pixel_art"`` all resolve
    to the same key.
    """
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def _user_presets_dir() -> Path:
    """Return the directory used for user-defined presets.

    The path is ``~/.bitmap_vector_studio`` and is created if it does
    not already exist.
    """
    directory = Path.home() / ".bitmap_vector_studio"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _user_presets_file() -> Path:
    """Return the full path to the user presets JSON file."""
    return _user_presets_dir() / "presets.json"


def _load_user_presets_raw() -> dict[str, dict[str, Any]]:
    """Load the raw user presets dictionary from disk.

    Returns an empty dict when the file does not exist or contains
    invalid JSON so that callers can treat it as a fresh store.
    """
    path = _user_presets_file()
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def _save_user_presets_raw(data: dict[str, dict[str, Any]]) -> None:
    """Persist the raw user presets dictionary to disk atomically."""
    path = _user_presets_file()
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    tmp.replace(path)


def _trace_options_to_dict(options: TraceOptions) -> dict[str, Any]:
    """Serialize a *TraceOptions* instance to a plain dictionary."""
    return asdict(options)


def _trace_options_from_dict(data: dict[str, Any]) -> TraceOptions:
    """Reconstruct a *TraceOptions* instance from a plain dictionary.

    Unknown keys are ignored so that forward-compatible imports do not
    break when older code encounters newer fields.
    """
    known = {f.name for f in TraceOptions.__dataclass_fields__.values()}
    clean = {k: v for k, v in data.items() if k in known}
    return TraceOptions(**clean)


def save_preset(name: str, options: TraceOptions, description: str = "") -> None:
    """Save a user-defined preset.

    Args:
        name: Preset identifier. It is normalised internally so that
            ``"My Preset"`` and ``"my_preset"`` map to the same entry.
        options: The *TraceOptions* values to store.
        description: Optional human-readable explanation.

    Raises:
        TypeError: If *options* is not a *TraceOptions* instance.
    """
    if not isinstance(options, TraceOptions):
        raise TypeError("options must be a TraceOptions instance")
    key = _normalize_preset_name(name)
    store = _load_user_presets_raw()
    store[key] = {
        "options": _trace_options_to_dict(options),
        "description": description.strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_user_presets_raw(store)


def load_preset(name: str) -> TraceOptions:
    """Load a preset by name, searching user presets first then built-ins.

    Args:
        name: Preset identifier (normalised the same way as
            :func:`save_preset`).

    Returns:
        A *TraceOptions* instance.

    Raises:
        ValueError: If no preset with the given name exists.
    """
    key = _normalize_preset_name(name)
    store = _load_user_presets_raw()
    entry = store.get(key)
    if entry is not None:
        return _trace_options_from_dict(entry["options"])
    if key in PRESETS:
        return PRESETS[key]
    valid = ", ".join(sorted(get_all_presets()))
    raise ValueError(f"Unknown preset '{name}'. Valid presets: {valid}.")


def delete_preset(name: str) -> None:
    """Delete a user-defined preset.

    Built-in presets cannot be deleted; calling this on a built-in name
    is a no-op.

    Args:
        name: Preset identifier to remove.
    """
    key = _normalize_preset_name(name)
    store = _load_user_presets_raw()
    store.pop(key, None)
    _save_user_presets_raw(store)


def list_user_presets() -> dict[str, dict[str, Any]]:
    """Return a dictionary of all user-defined presets.

    The returned structure mirrors the on-disk JSON format::

        {
            "preset_name": {
                "options": {...},
                "description": "...",
                "created_at": "...",
            }
        }
    """
    return _load_user_presets_raw()


def preset_exists(name: str) -> bool:
    """Check whether a preset (user or built-in) exists.

    Args:
        name: Preset identifier to test.

    Returns:
        ``True`` if the preset exists, otherwise ``False``.
    """
    key = _normalize_preset_name(name)
    if key in _load_user_presets_raw():
        return True
    return key in PRESETS


def get_all_presets() -> dict[str, TraceOptions]:
    """Return the union of built-in and user-defined presets.

    User presets override built-in presets when names collide.

    Returns:
        Mapping from normalised preset name to *TraceOptions*.
    """
    result = dict(PRESETS)
    for key, entry in _load_user_presets_raw().items():
        result[key] = _trace_options_from_dict(entry["options"])
    return result


def export_presets(path: Path) -> None:
    """Export all user-defined presets to a JSON file.

    Args:
        path: Destination file path. Parent directories are created
            automatically.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _load_user_presets_raw()
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")


def import_presets(path: Path, overwrite: bool = False) -> None:
    """Import presets from a JSON file into the user preset store.

    Args:
        path: Source file path.
        overwrite: When ``False`` (default), existing user presets with
            the same name are skipped. When ``True``, they are replaced
            by the imported values.

    Raises:
        FileNotFoundError: If *path* does not exist.
        ValueError: If the file does not contain a valid JSON object.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Import file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("Imported presets file must contain a JSON object")
    current = _load_user_presets_raw()
    for key, entry in data.items():
        if key in current and not overwrite:
            continue
        if isinstance(entry, dict) and "options" in entry:
            current[key] = entry
        else:
            # Gracefully handle bare option dumps by wrapping them.
            current[key] = {
                "options": entry if isinstance(entry, dict) else {},
                "description": "",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
    _save_user_presets_raw(current)
