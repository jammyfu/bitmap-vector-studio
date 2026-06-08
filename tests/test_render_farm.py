from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vector_studio.models import TraceOptions
from vector_studio.render_farm import (
    DistributedBatch,
    RenderFarm,
    RenderTask,
    WorkerNode,
    WorkerServer,
    start_worker_server,
)


class TestRenderTask:
    def test_task_defaults(self):
        task = RenderTask(
            task_id="abc",
            input_path=Path("in.png"),
            output_path=Path("out.svg"),
            options=TraceOptions(),
        )
        assert task.status == "pending"
        assert task.priority == 0
        assert task.assigned_worker is None
        assert task.started_at is None
        assert task.completed_at is None

    def test_task_to_dict(self):
        task = RenderTask(
            task_id="abc",
            input_path=Path("in.png"),
            output_path=Path("out.svg"),
            options=TraceOptions(),
            status="running",
            assigned_worker="w1",
        )
        d = task.to_dict()
        assert d["task_id"] == "abc"
        assert d["status"] == "running"
        assert d["assigned_worker"] == "w1"
        assert d["input_path"] == str(Path("in.png"))
        assert d["options"]["colormode"] == "color"

    def test_task_from_dict(self):
        d = {
            "task_id": "xyz",
            "input_path": "/tmp/in.jpg",
            "output_path": "/tmp/out.svg",
            "options": {"colormode": "binary", "filter_speckle": 2},
            "priority": 5,
            "status": "completed",
            "assigned_worker": "w2",
            "started_at": "2024-01-01T00:00:00",
            "completed_at": "2024-01-01T00:01:00",
        }
        task = RenderTask.from_dict(d)
        assert task.task_id == "xyz"
        assert task.options.colormode == "binary"
        assert task.options.filter_speckle == 2
        assert task.priority == 5
        assert task.status == "completed"


class TestWorkerNode:
    def test_is_alive_fresh(self):
        worker = WorkerNode("w1", "127.0.0.1", 9000)
        assert worker.is_alive(timeout=30.0) is True

    def test_is_alive_stale(self):
        worker = WorkerNode("w1", "127.0.0.1", 9000)
        worker.last_heartbeat = time.monotonic() - 60.0
        assert worker.is_alive(timeout=30.0) is False

    def test_update_heartbeat(self):
        worker = WorkerNode("w1", "127.0.0.1", 9000)
        old = worker.last_heartbeat
        time.sleep(0.01)
        worker.update_heartbeat()
        assert worker.last_heartbeat > old

    def test_to_dict(self):
        worker = WorkerNode("w1", "127.0.0.1", 9000, capacity=8)
        d = worker.to_dict()
        assert d["worker_id"] == "w1"
        assert d["host"] == "127.0.0.1"
        assert d["port"] == 9000
        assert d["capacity"] == 8
        assert d["alive"] is True

    def test_get_status_http_error(self):
        worker = WorkerNode("w1", "127.0.0.1", 9000)
        status = worker.get_status()
        assert status["alive"] is False
        assert status["worker_id"] == "w1"


class TestRenderFarm:
    def test_register_worker(self):
        farm = RenderFarm()
        w = WorkerNode("w1", "127.0.0.1", 9000)
        assert farm.register_worker(w) is True
        assert farm.register_worker(w) is False

    def test_unregister_worker(self):
        farm = RenderFarm()
        w = WorkerNode("w1", "127.0.0.1", 9000)
        farm.register_worker(w)
        assert farm.unregister_worker("w1") is True
        assert farm.unregister_worker("w1") is False

    def test_submit_task_no_worker(self):
        farm = RenderFarm()
        task = RenderTask(
            task_id="",
            input_path=Path("in.png"),
            output_path=Path("out.svg"),
            options=TraceOptions(),
        )
        tid = farm.submit_task(task)
        assert tid
        assert farm.get_task_status(tid)["status"] == "pending"

    def test_submit_task_with_worker(self):
        farm = RenderFarm()
        w = WorkerNode("w1", "127.0.0.1", 9000)
        farm.register_worker(w)
        task = RenderTask(
            task_id="",
            input_path=Path("in.png"),
            output_path=Path("out.svg"),
            options=TraceOptions(),
        )
        with patch.object(w, "submit_task", return_value=True):
            tid = farm.submit_task(task)
        assert farm.get_task_status(tid)["status"] == "running"
        assert farm.get_task_status(tid)["assigned_worker"] == "w1"

    def test_load_balance_prefers_low_load(self):
        farm = RenderFarm()
        w1 = WorkerNode("w1", "127.0.0.1", 9001, capacity=4)
        w2 = WorkerNode("w2", "127.0.0.1", 9002, capacity=4)
        w1.current_load = 3
        w2.current_load = 1
        farm.register_worker(w1)
        farm.register_worker(w2)
        best = farm.load_balance()
        assert best is not None
        assert best.worker_id == "w2"

    def test_load_balance_no_alive_workers(self):
        farm = RenderFarm()
        w = WorkerNode("w1", "127.0.0.1", 9000)
        w.last_heartbeat = time.monotonic() - 60.0
        farm.register_worker(w)
        assert farm.load_balance() is None

    def test_heartbeat_check(self):
        farm = RenderFarm()
        w1 = WorkerNode("w1", "127.0.0.1", 9000)
        w2 = WorkerNode("w2", "127.0.0.1", 9001)
        w2.last_heartbeat = time.monotonic() - 60.0
        farm.register_worker(w1)
        farm.register_worker(w2)
        dead = farm.heartbeat_check(timeout=30.0)
        assert dead == ["w2"]

    def test_get_farm_status(self):
        farm = RenderFarm()
        w = WorkerNode("w1", "127.0.0.1", 9000)
        farm.register_worker(w)
        task = RenderTask(
            task_id="t1",
            input_path=Path("in.png"),
            output_path=Path("out.svg"),
            options=TraceOptions(),
            status="completed",
        )
        farm.submit_task(task)
        status = farm.get_farm_status()
        assert status["summary"]["total_workers"] == 1
        assert status["summary"]["completed"] == 1

    def test_update_task(self):
        farm = RenderFarm()
        task = RenderTask(
            task_id="t1",
            input_path=Path("in.png"),
            output_path=Path("out.svg"),
            options=TraceOptions(),
        )
        farm.submit_task(task)
        assert farm.update_task("t1", "completed") is True
        assert farm.get_task_status("t1")["status"] == "completed"
        assert farm.update_task("missing", "completed") is False


class TestDistributedBatch:
    def test_split_batch(self, tmp_path: Path):
        (tmp_path / "a.png").write_bytes(b"fake")
        (tmp_path / "b.jpg").write_bytes(b"fake")
        (tmp_path / "c.txt").write_text("not an image")
        chunks = DistributedBatch.split_batch(tmp_path, chunk_size=1)
        assert len(chunks) == 2
        assert all(len(c) == 1 for c in chunks)

    def test_split_batch_empty(self, tmp_path: Path):
        chunks = DistributedBatch.split_batch(tmp_path, chunk_size=4)
        assert chunks == []

    def test_distribute_chunks(self, tmp_path: Path):
        farm = RenderFarm()
        w = WorkerNode("w1", "127.0.0.1", 9000)
        farm.register_worker(w)
        (tmp_path / "a.png").write_bytes(b"fake")
        chunks = [[tmp_path / "a.png"]]
        with patch.object(w, "submit_task", return_value=True):
            tids = DistributedBatch.distribute_chunks(
                chunks, [w], farm, tmp_path / "out", preset="poster"
            )
        assert len(tids) == 1
        assert farm.get_task_status(tids[0])["status"] == "running"

    def test_collect_results(self, tmp_path: Path):
        farm = RenderFarm()
        task = RenderTask(
            task_id="t1",
            input_path=Path("in.png"),
            output_path=tmp_path / "out.svg",
            options=TraceOptions(),
            status="completed",
        )
        farm.submit_task(task)
        paths = DistributedBatch.collect_results(["t1"], farm, timeout=1.0)
        assert paths == [tmp_path / "out.svg"]


class TestWorkerServer:
    def test_start_worker_server(self):
        server = start_worker_server("127.0.0.1", 0, capacity=2, worker_id="test-w")
        assert server._worker.worker_id == "test-w"
        assert server._worker.capacity == 2
        server.shutdown_server()

    def test_worker_server_heartbeat(self):
        server = start_worker_server("127.0.0.1", 0, capacity=2)
        port = server.server_address[1]
        server_thread = MagicMock()
        import threading
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        try:
            import urllib.request
            url = f"http://127.0.0.1:{port}/worker/heartbeat"
            req = urllib.request.Request(url, method="POST")
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            assert data["ok"] is True
            assert server._worker.is_alive()
        finally:
            server.shutdown_server()

    def test_worker_server_status(self):
        server = start_worker_server("127.0.0.1", 0, capacity=2)
        port = server.server_address[1]
        import threading
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        try:
            import urllib.request
            url = f"http://127.0.0.1:{port}/worker/status"
            with urllib.request.urlopen(url, timeout=2) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            assert data["worker_id"] == server._worker.worker_id
            assert data["capacity"] == 2
        finally:
            server.shutdown_server()
