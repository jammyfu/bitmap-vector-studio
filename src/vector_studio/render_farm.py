from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .models import TraceOptions
from .presets import options_from_preset
from .task_queue import TaskQueue
from .tracer import SUPPORTED_EXTENSIONS, trace_image


@dataclass
class RenderTask:
    """Represents a single render job in the distributed farm."""

    task_id: str
    input_path: Path
    output_path: Path
    options: TraceOptions
    priority: int = 0
    status: str = "pending"  # pending | running | completed | failed | cancelled
    assigned_worker: str | None = None
    started_at: str | None = None
    completed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the task to a plain dictionary."""
        return {
            "task_id": self.task_id,
            "input_path": str(self.input_path),
            "output_path": str(self.output_path),
            "options": {
                "colormode": self.options.colormode,
                "hierarchical": self.options.hierarchical,
                "mode": self.options.mode,
                "filter_speckle": self.options.filter_speckle,
                "color_precision": self.options.color_precision,
                "layer_difference": self.options.layer_difference,
                "corner_threshold": self.options.corner_threshold,
                "length_threshold": self.options.length_threshold,
                "max_iterations": self.options.max_iterations,
                "splice_threshold": self.options.splice_threshold,
                "path_precision": self.options.path_precision,
            },
            "priority": self.priority,
            "status": self.status,
            "assigned_worker": self.assigned_worker,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RenderTask":
        """Deserialize a RenderTask from a dictionary."""
        opts = TraceOptions(**data.get("options", {}))
        return cls(
            task_id=data["task_id"],
            input_path=Path(data["input_path"]),
            output_path=Path(data["output_path"]),
            options=opts,
            priority=data.get("priority", 0),
            status=data.get("status", "pending"),
            assigned_worker=data.get("assigned_worker"),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
        )


class WorkerNode:
    """Represents a single worker node in the render farm."""

    def __init__(
        self,
        worker_id: str,
        host: str,
        port: int,
        capacity: int = 4,
    ) -> None:
        self.worker_id = worker_id
        self.host = host
        self.port = port
        self.capacity = capacity
        self.current_load = 0
        self.last_heartbeat = time.monotonic()
        self._lock = threading.Lock()

    def is_alive(self, timeout: float = 30.0) -> bool:
        """Check whether the worker is still alive based on heartbeat age.

        Parameters
        ----------
        timeout:
            Maximum seconds since last heartbeat to consider alive.

        Returns
        -------
        bool
            ``True`` if the worker has heartbeated within *timeout*.
        """
        return (time.monotonic() - self.last_heartbeat) < timeout

    def submit_task(self, task: RenderTask) -> bool:
        """Submit a render task to this worker via HTTP.

        Parameters
        ----------
        task:
            The render task to submit.

        Returns
        -------
        bool
            ``True`` if the worker accepted the task.
        """
        url = f"http://{self.host}:{self.port}/worker/task"
        payload = json.dumps(task.to_dict()).encode("utf-8")
        req = Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("accepted"):
                    with self._lock:
                        self.current_load += 1
                    return True
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            pass
        return False

    def get_status(self) -> dict[str, Any]:
        """Query the worker for its current status.

        Returns
        -------
        dict
            Status dictionary from the worker, or a fallback on error.
        """
        url = f"http://{self.host}:{self.port}/worker/status"
        try:
            with urlopen(url, timeout=5) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            return {
                "worker_id": self.worker_id,
                "current_load": self.current_load,
                "capacity": self.capacity,
                "alive": False,
            }

    def update_heartbeat(self) -> None:
        """Record a fresh heartbeat timestamp."""
        with self._lock:
            self.last_heartbeat = time.monotonic()

    def to_dict(self) -> dict[str, Any]:
        """Serialize worker metadata to a dictionary."""
        with self._lock:
            return {
                "worker_id": self.worker_id,
                "host": self.host,
                "port": self.port,
                "capacity": self.capacity,
                "current_load": self.current_load,
                "last_heartbeat": self.last_heartbeat,
                "alive": self.is_alive(),
            }


class RenderFarm:
    """Distributed render farm coordinator.

    Manages a pool of :class:`WorkerNode` instances, distributes
    :class:`RenderTask` jobs, and tracks their lifecycle.
    """

    def __init__(self, coordinator_url: str | None = None) -> None:
        self.coordinator_url = coordinator_url
        self._workers: dict[str, WorkerNode] = {}
        self._tasks: dict[str, RenderTask] = {}
        self._lock = threading.Lock()
        self._heartbeat_thread: threading.Thread | None = None
        self._shutdown = threading.Event()

    def register_worker(self, worker: WorkerNode) -> bool:
        """Register a new worker node with the farm.

        Parameters
        ----------
        worker:
            The worker to register.

        Returns
        -------
        bool
            ``True`` if the worker was newly registered.
        """
        with self._lock:
            if worker.worker_id in self._workers:
                return False
            self._workers[worker.worker_id] = worker
            return True

    def unregister_worker(self, worker_id: str) -> bool:
        """Remove a worker from the farm.

        Parameters
        ----------
        worker_id:
            Identifier of the worker to remove.

        Returns
        -------
        bool
            ``True`` if the worker existed and was removed.
        """
        with self._lock:
            return self._workers.pop(worker_id, None) is not None

    def submit_task(self, task: RenderTask) -> str:
        """Submit a render task to the farm.

        If a suitable worker is available the task is assigned
        immediately; otherwise it remains pending.

        Parameters
        ----------
        task:
            The render task to submit.  If *task_id* is empty a UUID
            is generated.

        Returns
        -------
        str
            The task ID.
        """
        if not task.task_id:
            task.task_id = str(uuid.uuid4())
        with self._lock:
            self._tasks[task.task_id] = task

        worker = self.load_balance()
        if worker is not None and worker.submit_task(task):
            with self._lock:
                task.assigned_worker = worker.worker_id
                task.status = "running"
                task.started_at = datetime.now(timezone.utc).isoformat()
        return task.task_id

    def get_task_status(self, task_id: str) -> dict[str, Any]:
        """Query the status of a task.

        Returns
        -------
        dict
            Task dictionary, or ``{"task_id": task_id, "status": "unknown"}``
            if not found.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return {"task_id": task_id, "status": "unknown"}
            return task.to_dict()

    def get_farm_status(self) -> dict[str, Any]:
        """Return a snapshot of the whole farm state.

        Returns
        -------
        dict
            Dictionary with ``workers``, ``tasks``, and summary counts.
        """
        with self._lock:
            workers = [w.to_dict() for w in self._workers.values()]
            tasks = [t.to_dict() for t in self._tasks.values()]
            pending = sum(1 for t in self._tasks.values() if t.status == "pending")
            running = sum(1 for t in self._tasks.values() if t.status == "running")
            completed = sum(1 for t in self._tasks.values() if t.status == "completed")
            failed = sum(1 for t in self._tasks.values() if t.status == "failed")
        return {
            "workers": workers,
            "tasks": tasks,
            "summary": {
                "total_workers": len(workers),
                "alive_workers": sum(1 for w in workers if w["alive"]),
                "total_tasks": len(tasks),
                "pending": pending,
                "running": running,
                "completed": completed,
                "failed": failed,
            },
        }

    def load_balance(self) -> WorkerNode | None:
        """Select the best worker for a new task.

        Chooses the alive worker with the lowest load ratio
        (*current_load* / *capacity*).

        Returns
        -------
        WorkerNode | None
            The selected worker, or ``None`` if no alive worker has
            spare capacity.
        """
        with self._lock:
            candidates = [
                w for w in self._workers.values()
                if w.is_alive() and w.current_load < w.capacity
            ]
        if not candidates:
            return None
        return min(candidates, key=lambda w: w.current_load / w.capacity)

    def heartbeat_check(self, timeout: float = 30.0) -> list[str]:
        """Check all workers and return IDs of those that timed out.

        Parameters
        ----------
        timeout:
            Heartbeat age threshold in seconds.

        Returns
        -------
        list[str]
            Worker IDs that failed the heartbeat check.
        """
        dead: list[str] = []
        with self._lock:
            workers = list(self._workers.values())
        for worker in workers:
            if not worker.is_alive(timeout):
                dead.append(worker.worker_id)
        return dead

    def update_task(self, task_id: str, status: str, result: dict[str, Any] | None = None) -> bool:
        """Update the status of a tracked task (called by workers or pollers).

        Parameters
        ----------
        task_id:
            Task identifier.
        status:
            New status string.
        result:
            Optional result metadata.

        Returns
        -------
        bool
            ``True`` if the task existed and was updated.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            task.status = status
            task.completed_at = datetime.now(timezone.utc).isoformat()
            if task.assigned_worker and status in ("completed", "failed", "cancelled"):
                worker = self._workers.get(task.assigned_worker)
                if worker is not None:
                    worker.current_load = max(0, worker.current_load - 1)
            return True

    def start_heartbeat_monitor(self, interval: float = 10.0) -> None:
        """Start a background thread that runs ``heartbeat_check`` periodically."""
        if self._heartbeat_thread is not None and self._heartbeat_thread.is_alive():
            return
        self._shutdown.clear()

        def _loop() -> None:
            while not self._shutdown.is_set():
                self.heartbeat_check()
                self._shutdown.wait(interval)

        self._heartbeat_thread = threading.Thread(target=_loop, daemon=True)
        self._heartbeat_thread.start()

    def stop_heartbeat_monitor(self) -> None:
        """Signal the heartbeat monitor thread to stop."""
        self._shutdown.set()


class DistributedBatch:
    """Utility for splitting and distributing batch conversion jobs."""

    @staticmethod
    def split_batch(input_dir: Path, chunk_size: int) -> list[list[Path]]:
        """Split all supported images in *input_dir* into chunks.

        Parameters
        ----------
        input_dir:
            Directory to scan for images.
        chunk_size:
            Maximum number of files per chunk.

        Returns
        -------
        list[list[Path]]
            List of chunks, each chunk is a list of image paths.
        """
        images = [
            path for path in input_dir.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        ]
        images.sort()
        chunks: list[list[Path]] = []
        for i in range(0, len(images), chunk_size):
            chunks.append(images[i : i + chunk_size])
        return chunks

    @staticmethod
    def distribute_chunks(
        chunks: list[list[Path]],
        workers: list[WorkerNode],
        farm: RenderFarm,
        output_dir: Path,
        preset: str = "poster",
    ) -> list[str]:
        """Distribute chunk tasks to workers via *farm*.

        Parameters
        ----------
        chunks:
            Lists of image paths produced by :meth:`split_batch`.
        workers:
            Available worker nodes.
        farm:
            The render farm coordinator to submit tasks through.
        output_dir:
            Base directory for SVG outputs.
        preset:
            Tracing preset to use for all tasks.

        Returns
        -------
        list[str]
            Task IDs for every submitted chunk.
        """
        opts = options_from_preset(preset)
        task_ids: list[str] = []
        for chunk in chunks:
            for image_path in chunk:
                out_path = (output_dir / image_path.name).with_suffix(".svg")
                task = RenderTask(
                    task_id=str(uuid.uuid4()),
                    input_path=image_path,
                    output_path=out_path,
                    options=opts,
                )
                task_ids.append(farm.submit_task(task))
        return task_ids

    @staticmethod
    def collect_results(task_ids: list[str], farm: RenderFarm, timeout: float | None = None) -> list[Path]:
        """Poll the farm until all *task_ids* reach a terminal state.

        Parameters
        ----------
        task_ids:
            Task identifiers to wait for.
        farm:
            Render farm coordinator.
        timeout:
            Maximum total seconds to wait, or ``None`` for no limit.

        Returns
        -------
        list[Path]
            Output paths of completed tasks.  Failed tasks are omitted.
        """
        deadline = time.monotonic() + timeout if timeout is not None else None
        completed: list[Path] = []
        remaining = set(task_ids)
        while remaining:
            if deadline is not None and time.monotonic() >= deadline:
                break
            for tid in list(remaining):
                status = farm.get_task_status(tid)
                if status["status"] == "completed":
                    completed.append(Path(status["output_path"]))
                    remaining.discard(tid)
                elif status["status"] in ("failed", "cancelled", "unknown"):
                    remaining.discard(tid)
            if remaining:
                time.sleep(0.5)
        return completed


# ---------------------------------------------------------------------------
# Simple worker HTTP server
# ---------------------------------------------------------------------------

class _WorkerHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler for a render-farm worker node."""

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress default logging to keep CLI output clean.
        pass

    def _json_response(self, data: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/worker/status":
            worker = self.server._worker  # type: ignore[attr-defined]
            self._json_response(worker.get_status())
        else:
            self._json_response({"error": "not found"}, 404)

    def do_POST(self) -> None:
        if self.path == "/worker/task":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError:
                self._json_response({"accepted": False, "error": "bad json"}, 400)
                return

            worker = self.server._worker  # type: ignore[attr-defined]
            task = RenderTask.from_dict(data)
            accepted = worker.submit_task(task)
            if accepted:
                # Enqueue for actual processing on the worker side.
                queue = self.server._queue  # type: ignore[attr-defined]
                queue.add_task(
                    task.input_path,
                    task.output_path,
                    task.options,
                )
            self._json_response({"accepted": accepted, "task_id": task.task_id})
        elif self.path == "/worker/heartbeat":
            worker = self.server._worker  # type: ignore[attr-defined]
            worker.update_heartbeat()
            self._json_response({"ok": True})
        else:
            self._json_response({"error": "not found"}, 404)


class WorkerServer(HTTPServer):
    """HTTP server that hosts a single :class:`WorkerNode`."""

    def __init__(self, worker: WorkerNode, server_address: tuple[str, int]) -> None:
        super().__init__(server_address, _WorkerHandler)
        self._worker = worker
        self._queue = TaskQueue(max_workers=worker.capacity)
        self._queue.start()
        self._serving = False

    def serve_forever(self, poll_interval: float = 0.5) -> None:
        """Start serving requests."""
        self._serving = True
        super().serve_forever(poll_interval)

    def shutdown_server(self) -> None:
        """Gracefully shut down the worker server and its task queue."""
        self._queue._shutdown.set()
        self._queue.wait_for_all(timeout=5.0)
        if self._serving:
            self.shutdown()
        else:
            self.server_close()


def start_worker_server(
    host: str,
    port: int,
    capacity: int = 4,
    worker_id: str | None = None,
) -> WorkerServer:
    """Start a blocking worker HTTP server.

    Parameters
    ----------
    host:
        Interface to bind.
    port:
        TCP port to listen on.
    capacity:
        Maximum concurrent tasks this worker accepts.
    worker_id:
        Optional worker identifier (auto-generated if omitted).

    Returns
    -------
    WorkerServer
        The running server instance.
    """
    wid = worker_id or str(uuid.uuid4())
    worker = WorkerNode(worker_id=wid, host=host, port=port, capacity=capacity)
    server = WorkerServer(worker, (host, port))
    return server
