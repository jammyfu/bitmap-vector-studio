from __future__ import annotations

import csv
import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from queue import Queue
from typing import Any

from .checkpoint import CheckpointManager
from .models import TraceOptions, TraceResult
from .tracer import SUPPORTED_EXTENSIONS, trace_image


@dataclass
class ConversionTask:
    """Represents a single conversion job in the task queue."""

    task_id: str
    input_path: Path
    output_path: Path
    options: TraceOptions
    status: str = "pending"  # pending | running | completed | failed | cancelled
    progress: float = 0.0  # 0.0 – 100.0
    result: TraceResult | None = None
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str | None = None
    completed_at: str | None = None
    optimize_level: str = "basic"
    _retry_count: int = field(default=0, repr=False)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the task to a plain dictionary."""
        return {
            "task_id": self.task_id,
            "input_path": str(self.input_path),
            "output_path": str(self.output_path),
            "status": self.status,
            "progress": self.progress,
            "result": {
                "svg_path": str(self.result.svg_path) if self.result else None,
                "elapsed_seconds": self.result.elapsed_seconds if self.result else None,
                "stats": self.result.stats if self.result else None,
            },
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class TaskQueue:
    """Thread-safe batch conversion queue with concurrency control and retries.

    The queue uses a background worker thread that pulls tasks from an internal
    ``queue.Queue``.  A ``threading.Semaphore`` limits the number of concurrent
    conversions.  Failed tasks are automatically retried up to *max_retries* times.

    Example
    -------
    >>> q = TaskQueue(max_workers=2)
    >>> q.add_task(Path("in.png"), Path("out.svg"), TraceOptions())
    >>> q.start()
    >>> q.wait_for_all()
    >>> q.export_report(Path("report.csv"))
    """

    def __init__(
        self,
        max_workers: int = 4,
        output_dir: Path | None = None,
        max_retries: int = 2,
        checkpoint_manager: CheckpointManager | None = None,
        queue_id: str | None = None,
    ) -> None:
        self.max_workers = max_workers
        self.output_dir = output_dir
        self.max_retries = max_retries
        self._queue: Queue[ConversionTask] = Queue()
        self._tasks: dict[str, ConversionTask] = {}
        self._lock = threading.Lock()
        self._semaphore = threading.Semaphore(max_workers)
        self._worker_thread: threading.Thread | None = None
        self._shutdown = threading.Event()
        self._paused = threading.Event()
        self._active_threads: list[threading.Thread] = []
        self._active_threads_lock = threading.Lock()
        self.checkpoint_manager = checkpoint_manager
        self.queue_id = queue_id or str(uuid.uuid4())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_task(
        self,
        input_path: Path | str,
        output_path: Path | str,
        options: TraceOptions,
        optimize_level: str = "basic",
        plugins: list[Any] | None = None,
    ) -> str:
        """Add a single conversion task to the queue.

        Returns the generated task ID.
        """
        task_id = str(uuid.uuid4())
        task = ConversionTask(
            task_id=task_id,
            input_path=Path(input_path),
            output_path=Path(output_path),
            options=options,
            optimize_level=optimize_level,
        )
        # Store plugins on the task instance dynamically.
        object.__setattr__(task, "_plugins", plugins or [])
        with self._lock:
            self._tasks[task_id] = task
        self._queue.put(task)
        # Auto-save checkpoint if manager is present.
        if self.checkpoint_manager is not None:
            try:
                self.checkpoint_manager.save_checkpoint(self.queue_id, list(self._tasks.values()))
            except Exception:  # noqa: BLE001
                pass
        return task_id

    def add_batch(
        self,
        input_dir: Path | str,
        output_dir: Path | str,
        preset: str = "poster",
        recursive: bool = False,
    ) -> list[str]:
        """Add all supported images in *input_dir* to the queue.

        Returns the list of generated task IDs.
        """
        from .presets import options_from_preset

        input_dir = Path(input_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        opts = options_from_preset(preset)

        iterator = input_dir.rglob("*") if recursive else input_dir.glob("*")
        images = [
            path for path in iterator if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        ]

        task_ids: list[str] = []
        for image_path in images:
            rel = image_path.relative_to(input_dir) if recursive else Path(image_path.name)
            out_path = (output_dir / rel).with_suffix(".svg")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            task_ids.append(self.add_task(image_path, out_path, opts))

        return task_ids

    def start(self) -> None:
        """Start the background worker thread that consumes the queue."""
        if self._worker_thread is not None and self._worker_thread.is_alive():
            return
        # Attempt to resume from a previous checkpoint.
        if self.checkpoint_manager is not None:
            restored = self.checkpoint_manager.load_checkpoint(self.queue_id)
            if restored:
                with self._lock:
                    for task in restored:
                        if task.status in ("pending", "running"):
                            task.status = "pending"
                            task.progress = 0.0
                            task.started_at = None
                            self._tasks[task.task_id] = task
                            self._queue.put(task)
                logger.info("Resumed %d tasks from checkpoint %s", len(restored), self.queue_id)
        self._shutdown.clear()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        # Start auto-save if a checkpoint manager is attached.
        if self.checkpoint_manager is not None:
            self.checkpoint_manager.auto_save(self.queue_id, list(self._tasks.values()))

    def pause(self) -> None:
        """Pause processing new tasks (running tasks continue)."""
        self._paused.set()

    def resume(self) -> None:
        """Resume processing paused tasks."""
        self._paused.clear()

    def cancel(self, task_id: str) -> bool:
        """Cancel a pending or running task.

        Returns ``True`` if the task was found and marked cancelled.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            if task.status in ("pending", "running"):
                task.status = "cancelled"
                task.completed_at = datetime.now(timezone.utc).isoformat()
                return True
            return False

    def get_status(self, task_id: str) -> dict[str, Any]:
        """Return the current status dictionary for *task_id*."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return {"task_id": task_id, "status": "unknown"}
            return task.to_dict()

    def get_all_status(self) -> list[dict[str, Any]]:
        """Return status dictionaries for every known task."""
        with self._lock:
            return [task.to_dict() for task in self._tasks.values()]

    def wait_for(self, task_id: str, timeout: float | None = None) -> ConversionTask:
        """Block until *task_id* reaches a terminal state.

        Raises ``KeyError`` if the task does not exist.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                raise KeyError(f"Task not found: {task_id}")

        deadline = time.monotonic() + timeout if timeout is not None else None
        while True:
            with self._lock:
                task = self._tasks[task_id]
                if task.status in ("completed", "failed", "cancelled"):
                    return task
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError(f"Timeout waiting for task {task_id}")
            time.sleep(0.05)

    def wait_for_all(self, timeout: float | None = None) -> list[ConversionTask]:
        """Block until every task reaches a terminal state.

        Returns the list of tasks in insertion order.
        """
        with self._lock:
            task_ids = list(self._tasks.keys())

        deadline = time.monotonic() + timeout if timeout is not None else None
        results: list[ConversionTask] = []
        for tid in task_ids:
            remaining = None
            if deadline is not None:
                remaining = max(0.0, deadline - time.monotonic())
            results.append(self.wait_for(tid, timeout=remaining))
        return results

    def export_report(self, path: Path | str) -> None:
        """Export a CSV report of all tasks to *path*."""
        path = Path(path)
        records = self.get_all_status()
        if not records:
            path.write_text("", encoding="utf-8")
            return

        headers = list(records[0].keys())
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for record in records:
                flat = {
                    k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                    for k, v in record.items()
                }
                writer.writerow(flat)

    # ------------------------------------------------------------------
    # Internal worker
    # ------------------------------------------------------------------

    def _worker_loop(self) -> None:
        """Main loop that pulls tasks and dispatches them to worker threads."""
        while not self._shutdown.is_set():
            try:
                task = self._queue.get(timeout=0.5)
            except Exception:
                continue

            # Wait while paused.
            while self._paused.is_set() and not self._shutdown.is_set():
                time.sleep(0.1)

            if self._shutdown.is_set():
                break

            # Skip already-cancelled tasks.
            with self._lock:
                if task.status == "cancelled":
                    self._queue.task_done()
                    continue

            # Acquire semaphore slot.
            self._semaphore.acquire()
            t = threading.Thread(target=self._run_task, args=(task,), daemon=True)
            with self._active_threads_lock:
                self._active_threads.append(t)
            t.start()

    def _run_task(self, task: ConversionTask) -> None:
        """Execute a single task with retry logic and progress updates."""
        try:
            with self._lock:
                if task.status == "cancelled":
                    return
                task.status = "running"
                task.started_at = datetime.now(timezone.utc).isoformat()
                task.progress = 10.0

            # Perform conversion.
            plugins = getattr(task, "_plugins", None)
            kwargs: dict[str, Any] = {"optimize_level": task.optimize_level}
            if plugins is not None:
                kwargs["plugins"] = plugins
            result = trace_image(
                task.input_path,
                task.output_path,
                task.options,
                **kwargs,
            )

            with self._lock:
                task.result = result
                task.progress = 100.0
                task.status = "completed"
                task.completed_at = datetime.now(timezone.utc).isoformat()

        except Exception as exc:
            with self._lock:
                task._retry_count += 1
                if task._retry_count <= self.max_retries:
                    task.status = "pending"
                    task.error = None
                    task.progress = 0.0
                else:
                    task.error = str(exc)
                    task.status = "failed"
                    task.completed_at = datetime.now(timezone.utc).isoformat()

            if task.status == "pending":
                # Re-queue for retry.
                self._queue.put(task)

        finally:
            self._semaphore.release()
            with self._active_threads_lock:
                try:
                    self._active_threads.remove(threading.current_thread())
                except ValueError:
                    pass
            self._queue.task_done()
            # Update checkpoint after task completion if manager is present.
            if self.checkpoint_manager is not None:
                try:
                    self.checkpoint_manager.save_checkpoint(self.queue_id, list(self._tasks.values()))
                except Exception:  # noqa: BLE001
                    pass
