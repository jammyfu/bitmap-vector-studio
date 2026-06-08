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
from typing import Any, Callable, TYPE_CHECKING

from .models import TraceOptions, TraceResult

if TYPE_CHECKING:
    from .task_queue import ConversionTask

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
# Helpers
# ---------------------------------------------------------------------------

def _default_checkpoint_dir() -> Path:
    """Return the default checkpoint directory."""
    directory = Path.home() / ".bitmap_vector_studio" / "checkpoints"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


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


def _serialize_task(task: ConversionTask) -> dict[str, Any]:
    """Serialize a ConversionTask to a plain dictionary."""
    data = {
        "task_id": task.task_id,
        "input_path": str(task.input_path),
        "output_path": str(task.output_path),
        "options": _serialize_trace_options(task.options),
        "status": task.status,
        "progress": task.progress,
        "error": task.error,
        "created_at": task.created_at,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "optimize_level": task.optimize_level,
        "_retry_count": task._retry_count,
    }
    if task.result is not None:
        data["result"] = {
            "input_path": str(task.result.input_path),
            "svg_path": str(task.result.svg_path),
            "engine": task.result.engine,
            "elapsed_seconds": task.result.elapsed_seconds,
            "stats": task.result.stats,
            "pdf_path": str(task.result.pdf_path) if task.result.pdf_path else None,
            "png_path": str(task.result.png_path) if task.result.png_path else None,
            "eps_path": str(task.result.eps_path) if task.result.eps_path else None,
        }
    return data


def _deserialize_task(data: dict[str, Any]) -> ConversionTask:
    """Reconstruct a ConversionTask from a plain dictionary."""
    from .task_queue import ConversionTask
    task = ConversionTask(
        task_id=data["task_id"],
        input_path=Path(data["input_path"]),
        output_path=Path(data["output_path"]),
        options=_deserialize_trace_options(data.get("options", {})),
        status=data.get("status", "pending"),
        progress=data.get("progress", 0.0),
        error=data.get("error"),
        created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
        started_at=data.get("started_at"),
        completed_at=data.get("completed_at"),
        optimize_level=data.get("optimize_level", "basic"),
        _retry_count=data.get("_retry_count", 0),
    )
    # Restore result if present
    result_data = data.get("result")
    if result_data and result_data.get("svg_path"):
        task.result = TraceResult(
            input_path=Path(result_data.get("input_path", data["input_path"])),
            svg_path=Path(result_data["svg_path"]),
            engine=result_data.get("engine", "unknown"),
            elapsed_seconds=result_data.get("elapsed_seconds", 0.0),
            stats=result_data.get("stats", {}),
            pdf_path=Path(result_data["pdf_path"]) if result_data.get("pdf_path") else None,
            png_path=Path(result_data["png_path"]) if result_data.get("png_path") else None,
            eps_path=Path(result_data["eps_path"]) if result_data.get("eps_path") else None,
        )
    return task


# ---------------------------------------------------------------------------
# CheckpointManager
# ---------------------------------------------------------------------------

class CheckpointManager:
    """Manages persistent checkpoints for batch conversion tasks.

    Checkpoints are stored as JSON files in *checkpoint_dir* (default
    ``~/.bitmap_vector_studio/checkpoints/``).  Each checkpoint captures the
    full state of a task queue so that interrupted batches can be resumed.
    """

    def __init__(self, checkpoint_dir: Path | None = None) -> None:
        """Create a new checkpoint manager.

        Parameters
        ----------
        checkpoint_dir:
            Directory where checkpoint files are written.  When ``None`` the
            default user-level directory is used.
        """
        self.checkpoint_dir = checkpoint_dir or _default_checkpoint_dir()
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._auto_save_timers: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def _checkpoint_path(self, queue_id: str) -> Path:
        """Return the filesystem path for a given queue checkpoint."""
        # Sanitize queue_id for safe filename usage.
        safe_id = queue_id.replace("/", "_").replace("\\", "_")
        return self.checkpoint_dir / f"{safe_id}.json"

    def save_checkpoint(self, queue_id: str, tasks: list[ConversionTask]) -> Path:
        """Persist the current task list to a checkpoint file.

        Parameters
        ----------
        queue_id:
            Identifier for the queue / batch job.
        tasks:
            Current list of :class:`ConversionTask` instances.

        Returns
        -------
        Path
            The written checkpoint file path.
        """
        path = self._checkpoint_path(queue_id)
        payload = {
            "queue_id": queue_id,
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "tasks": [_serialize_task(t) for t in tasks],
        }
        with self._lock:
            with path.open("w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
        logger.info("Checkpoint saved for queue %s -> %s", queue_id, path)
        return path

    def load_checkpoint(self, queue_id: str) -> list[ConversionTask] | None:
        """Restore tasks from a checkpoint file.

        Parameters
        ----------
        queue_id:
            Identifier for the queue / batch job.

        Returns
        -------
        list[ConversionTask] | None
            The restored task list, or ``None`` if no checkpoint exists.
        """
        path = self._checkpoint_path(queue_id)
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as fh:
                payload = json.load(fh)
            tasks = [_deserialize_task(t) for t in payload.get("tasks", [])]
            logger.info("Checkpoint loaded for queue %s (%d tasks)", queue_id, len(tasks))
            return tasks
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load checkpoint %s: %s", path, exc)
            return None

    def list_checkpoints(self) -> list[dict[str, Any]]:
        """List all available checkpoints with metadata.

        Returns
        -------
        list[dict[str, Any]]
            Each dict contains ``queue_id``, ``saved_at``, ``task_count``,
            and ``path``.
        """
        results: list[dict[str, Any]] = []
        for path in sorted(self.checkpoint_dir.glob("*.json")):
            try:
                with path.open("r", encoding="utf-8") as fh:
                    payload = json.load(fh)
                results.append(
                    {
                        "queue_id": payload.get("queue_id", path.stem),
                        "saved_at": payload.get("saved_at"),
                        "task_count": len(payload.get("tasks", [])),
                        "path": str(path),
                    }
                )
            except Exception:  # noqa: BLE001
                continue
        return results

    def delete_checkpoint(self, queue_id: str) -> bool:
        """Delete a checkpoint file.

        Returns
        -------
        bool
            ``True`` if the file existed and was removed.
        """
        path = self._checkpoint_path(queue_id)
        if path.exists():
            path.unlink()
            logger.info("Checkpoint deleted for queue %s", queue_id)
            return True
        return False

    def auto_save(
        self,
        queue_id: str,
        tasks: list[ConversionTask],
        interval: int = 30,
    ) -> None:
        """Start a recurring auto-save timer.

        The timer fires every *interval* seconds and calls
        :meth:`save_checkpoint`.  Previous timers for the same *queue_id*
        are cancelled automatically.

        Parameters
        ----------
        queue_id:
            Identifier for the queue / batch job.
        tasks:
            Current list of tasks.  Note: the list is captured by reference,
            so mutations are visible to the timer callback.
        interval:
            Seconds between auto-save attempts (default 30).
        """
        with self._lock:
            old_timer = self._auto_save_timers.get(queue_id)
            if old_timer is not None:
                old_timer.cancel()

        def _tick() -> None:
            try:
                self.save_checkpoint(queue_id, tasks)
            except Exception:  # noqa: BLE001
                pass
            # Reschedule
            with self._lock:
                if queue_id in self._auto_save_timers:
                    t = threading.Timer(float(interval), _tick)
                    t.daemon = True
                    t.start()
                    self._auto_save_timers[queue_id] = t

        t = threading.Timer(float(interval), _tick)
        t.daemon = True
        with self._lock:
            self._auto_save_timers[queue_id] = t
        t.start()

    def stop_auto_save(self, queue_id: str) -> None:
        """Cancel the auto-save timer for *queue_id*."""
        with self._lock:
            timer = self._auto_save_timers.pop(queue_id, None)
            if timer is not None:
                timer.cancel()

    def stop_all_auto_save(self) -> None:
        """Cancel all active auto-save timers."""
        with self._lock:
            for timer in self._auto_save_timers.values():
                timer.cancel()
            self._auto_save_timers.clear()
