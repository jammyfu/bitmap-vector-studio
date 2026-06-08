from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import TraceOptions

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _default_workspace_dir() -> Path:
    """Return the default workspace directory."""
    directory = Path.home() / ".bitmap_vector_studio" / "workspaces"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _crash_file_path() -> Path:
    """Return the path used for crash recovery state."""
    return Path.home() / ".bitmap_vector_studio" / ".crash_recovery.json"


def _serialize_trace_options(options: TraceOptions) -> dict[str, Any]:
    """Serialize TraceOptions to a plain dictionary."""
    return {
        "colormode": options.colormode,
        "hierarchical": options.hierarchical,
        "mode": options.mode,
        "filter_speckle": options.filter_speckle,
        "color_precision": options.color_precision,
        "layer_difference": options.layer_difference,
        "corner_threshold": options.corner_threshold,
        "length_threshold": options.length_threshold,
        "max_iterations": options.max_iterations,
        "splice_threshold": options.splice_threshold,
        "path_precision": options.path_precision,
        "denoise": options.denoise,
        "posterize": options.posterize,
        "max_input_side": options.max_input_side,
        "alpha_background": options.alpha_background,
    }


def _deserialize_trace_options(data: dict[str, Any]) -> TraceOptions:
    """Reconstruct TraceOptions from a plain dictionary."""
    known = {f.name for f in TraceOptions.__dataclass_fields__.values()}
    clean = {k: v for k, v in data.items() if k in known}
    return TraceOptions(**clean)


# ---------------------------------------------------------------------------
# Workspace dataclass
# ---------------------------------------------------------------------------

@dataclass
class Workspace:
    """Represents a saved application work session."""

    open_files: list[str] = field(default_factory=list)
    current_preset: str = "poster"
    current_options: TraceOptions = field(default_factory=TraceOptions)
    queue_state: list[dict[str, Any]] = field(default_factory=list)
    sidebar_width: int = 240
    preview_mode: str = "split"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Serialize the workspace to a plain dictionary."""
        data = asdict(self)
        data["current_options"] = _serialize_trace_options(self.current_options)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Workspace":
        """Reconstruct a Workspace from a plain dictionary."""
        opts_data = data.get("current_options", {})
        if isinstance(opts_data, dict):
            current_options = _deserialize_trace_options(opts_data)
        else:
            current_options = TraceOptions()
        return cls(
            open_files=list(data.get("open_files", [])),
            current_preset=data.get("current_preset", "poster"),
            current_options=current_options,
            queue_state=list(data.get("queue_state", [])),
            sidebar_width=int(data.get("sidebar_width", 240)),
            preview_mode=data.get("preview_mode", "split"),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
        )


# ---------------------------------------------------------------------------
# WorkspaceManager
# ---------------------------------------------------------------------------

class WorkspaceManager:
    """Persist and restore :class:`Workspace` snapshots."""

    def __init__(self, workspace_dir: Path | None = None) -> None:
        """Create a new manager.

        Parameters
        ----------
        workspace_dir:
            Directory where workspace JSON files are stored.  Defaults to
            ``~/.bitmap_vector_studio/workspaces/``.
        """
        self.workspace_dir = workspace_dir or _default_workspace_dir()
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self._auto_save_timer: threading.Timer | None = None
        self._current_workspace: Workspace | None = None
        self._lock = threading.Lock()

    def _workspace_path(self, name: str) -> Path:
        """Return the filesystem path for a named workspace."""
        safe_name = name.replace("/", "_").replace("\\", "_")
        return self.workspace_dir / f"{safe_name}.json"

    def save(self, workspace: Workspace, name: str | None = None) -> Path:
        """Save a workspace to disk.

        Parameters
        ----------
        workspace:
            The workspace to persist.
        name:
            Custom file name (without extension).  When ``None`` a timestamped
            name is generated automatically.

        Returns
        -------
        Path
            The written file path.
        """
        if name is None:
            name = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        workspace.timestamp = datetime.now(timezone.utc).isoformat()
        path = self._workspace_path(name)
        with self._lock:
            with path.open("w", encoding="utf-8") as fh:
                json.dump(workspace.to_dict(), fh, indent=2, ensure_ascii=False)
        logger.info("Workspace saved: %s", path)
        return path

    def load(self, name: str) -> Workspace | None:
        """Load a workspace by name.

        Returns
        -------
        Workspace | None
            The restored workspace, or ``None`` if the file does not exist
            or is unreadable.
        """
        path = self._workspace_path(name)
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            return Workspace.from_dict(data)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load workspace %s: %s", path, exc)
            return None

    def list_workspaces(self) -> list[dict[str, Any]]:
        """List all saved workspaces with metadata.

        Returns
        -------
        list[dict[str, Any]]
            Each dict contains ``name``, ``timestamp``, and ``path``.
        """
        results: list[dict[str, Any]] = []
        for path in sorted(self.workspace_dir.glob("*.json")):
            try:
                with path.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
                results.append(
                    {
                        "name": path.stem,
                        "timestamp": data.get("timestamp"),
                        "path": str(path),
                    }
                )
            except Exception:  # noqa: BLE001
                continue
        return results

    def delete(self, name: str) -> bool:
        """Delete a saved workspace.

        Returns
        -------
        bool
            ``True`` if the file existed and was removed.
        """
        path = self._workspace_path(name)
        if path.exists():
            path.unlink()
            logger.info("Workspace deleted: %s", path)
            return True
        return False

    def auto_save_current(self, workspace: Workspace, interval: int = 60) -> None:
        """Start a recurring timer that saves *workspace* every *interval* seconds.

        The most recent workspace reference is captured, so mutations are
        persisted automatically.
        """
        with self._lock:
            if self._auto_save_timer is not None:
                self._auto_save_timer.cancel()
            self._current_workspace = workspace

        def _tick() -> None:
            try:
                with self._lock:
                    ws = self._current_workspace
                if ws is not None:
                    self.save(ws, name="auto_save")
            except Exception:  # noqa: BLE001
                pass
            # Reschedule
            with self._lock:
                if self._current_workspace is not None:
                    t = threading.Timer(float(interval), _tick)
                    t.daemon = True
                    t.start()
                    self._auto_save_timer = t

        t = threading.Timer(float(interval), _tick)
        t.daemon = True
        with self._lock:
            self._auto_save_timer = t
        t.start()

    def stop_auto_save(self) -> None:
        """Cancel the active auto-save timer."""
        with self._lock:
            if self._auto_save_timer is not None:
                self._auto_save_timer.cancel()
                self._auto_save_timer = None
            self._current_workspace = None

    def restore_last(self) -> Workspace | None:
        """Restore the most recently saved workspace.

        Prefers ``auto_save`` when present, otherwise picks the workspace
        with the newest timestamp.

        Returns
        -------
        Workspace | None
        """
        auto = self.load("auto_save")
        if auto is not None:
            return auto
        workspaces = self.list_workspaces()
        if not workspaces:
            return None
        # Sort by timestamp descending
        workspaces.sort(key=lambda w: w.get("timestamp") or "", reverse=True)
        return self.load(workspaces[0]["name"])


# ---------------------------------------------------------------------------
# CrashRecovery
# ---------------------------------------------------------------------------

class CrashRecovery:
    """Save and restore application state around unexpected crashes."""

    def __init__(self, manager: WorkspaceManager | None = None) -> None:
        """Create a crash recovery helper.

        Parameters
        ----------
        manager:
            Optional :class:`WorkspaceManager` to use for normal workspace
            operations.  When ``None`` a default instance is created.
        """
        self.manager = manager or WorkspaceManager()

    def save_crash_state(self, workspace: Workspace) -> Path:
        """Persist *workspace* to the crash recovery file.

        This should be called periodically (e.g. from a timer) so that the
        latest state is available if the process terminates unexpectedly.

        Returns
        -------
        Path
            The crash recovery file path.
        """
        path = _crash_file_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "crash_timestamp": datetime.now(timezone.utc).isoformat(),
            "workspace": workspace.to_dict(),
        }
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        logger.info("Crash state saved to %s", path)
        return path

    def check_crash_recovery(self) -> Workspace | None:
        """Check whether a crash recovery file exists and return it.

        Returns
        -------
        Workspace | None
            The recovered workspace, or ``None`` if no crash file exists.
        """
        path = _crash_file_path()
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as fh:
                payload = json.load(fh)
            ws_data = payload.get("workspace")
            if not ws_data:
                return None
            return Workspace.from_dict(ws_data)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to read crash recovery file: %s", exc)
            return None

    def clear_crash_state(self) -> bool:
        """Remove the crash recovery file.

        Returns
        -------
        bool
            ``True`` if the file existed and was removed.
        """
        path = _crash_file_path()
        if path.exists():
            path.unlink()
            logger.info("Crash state cleared")
            return True
        return False
