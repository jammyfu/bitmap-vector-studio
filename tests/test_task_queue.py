from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vector_studio.models import TraceOptions, TraceResult
from vector_studio.task_queue import ConversionTask, TaskQueue


class TestConversionTask:
    def test_task_defaults(self):
        task = ConversionTask(
            task_id="abc",
            input_path=Path("in.png"),
            output_path=Path("out.svg"),
            options=TraceOptions(),
        )
        assert task.status == "pending"
        assert task.progress == 0.0
        assert task.result is None
        assert task.error is None
        assert task.started_at is None
        assert task.completed_at is None

    def test_task_to_dict(self):
        task = ConversionTask(
            task_id="abc",
            input_path=Path("in.png"),
            output_path=Path("out.svg"),
            options=TraceOptions(),
            status="completed",
            progress=100.0,
            result=TraceResult(
                input_path=Path("in.png"),
                svg_path=Path("out.svg"),
                engine="python-vtracer",
                elapsed_seconds=1.0,
            ),
        )
        d = task.to_dict()
        assert d["task_id"] == "abc"
        assert d["status"] == "completed"
        assert d["progress"] == 100.0
        assert d["result"]["svg_path"] == str(Path("out.svg"))


class TestTaskQueueAdd:
    def test_add_task_returns_unique_id(self):
        q = TaskQueue()
        id1 = q.add_task(Path("a.png"), Path("a.svg"), TraceOptions())
        id2 = q.add_task(Path("b.png"), Path("b.svg"), TraceOptions())
        assert id1 != id2
        assert isinstance(id1, str)

    def test_add_batch_finds_images(self, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        (input_dir / "img1.png").write_bytes(b"fake")
        (input_dir / "img2.jpg").write_bytes(b"fake")
        (input_dir / "readme.txt").write_text("not an image")

        q = TaskQueue()
        ids = q.add_batch(input_dir, output_dir, preset="poster")
        assert len(ids) == 2

    def test_add_batch_recursive(self, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        sub = input_dir / "sub"
        sub.mkdir()
        output_dir = tmp_path / "output"
        (sub / "deep.png").write_bytes(b"fake")

        q = TaskQueue()
        ids = q.add_batch(input_dir, output_dir, preset="poster", recursive=True)
        assert len(ids) == 1


class TestTaskQueueLifecycle:
    def test_task_lifecycle_completed(self, tmp_path):
        img = tmp_path / "img.png"
        img.write_bytes(b"fake")
        out = tmp_path / "out.svg"

        mock_result = TraceResult(
            input_path=img,
            svg_path=out,
            engine="python-vtracer",
            elapsed_seconds=0.5,
            stats={"paths": 3},
        )

        q = TaskQueue(max_workers=1)
        tid = q.add_task(img, out, TraceOptions())
        with patch("vector_studio.task_queue.trace_image", return_value=mock_result):
            q.start()
            task = q.wait_for(tid, timeout=5.0)

        assert task.status == "completed"
        assert task.result is not None
        assert task.result.elapsed_seconds == 0.5
        assert task.progress == 100.0
        assert task.started_at is not None
        assert task.completed_at is not None

    def test_task_lifecycle_failed(self, tmp_path):
        img = tmp_path / "img.png"
        img.write_bytes(b"fake")
        out = tmp_path / "out.svg"

        q = TaskQueue(max_workers=1, max_retries=0)
        tid = q.add_task(img, out, TraceOptions())
        with patch("vector_studio.task_queue.trace_image", side_effect=RuntimeError("boom")):
            q.start()
            task = q.wait_for(tid, timeout=5.0)

        assert task.status == "failed"
        assert task.error == "boom"
        assert task.completed_at is not None

    def test_cancel_pending_task(self, tmp_path):
        q = TaskQueue()
        tid = q.add_task(tmp_path / "img.png", tmp_path / "out.svg", TraceOptions())
        assert q.cancel(tid) is True
        status = q.get_status(tid)
        assert status["status"] == "cancelled"

    def test_cancel_nonexistent_task(self):
        q = TaskQueue()
        assert q.cancel("does-not-exist") is False

    def test_get_status_unknown_task(self):
        q = TaskQueue()
        status = q.get_status("unknown")
        assert status["status"] == "unknown"


class TestTaskQueueRetry:
    def test_retry_succeeds_eventually(self, tmp_path):
        img = tmp_path / "img.png"
        img.write_bytes(b"fake")
        out = tmp_path / "out.svg"

        mock_result = TraceResult(
            input_path=img,
            svg_path=out,
            engine="python-vtracer",
            elapsed_seconds=0.5,
            stats={"paths": 3},
        )

        call_count = 0

        def _side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("transient")
            return mock_result

        q = TaskQueue(max_workers=1, max_retries=2)
        tid = q.add_task(img, out, TraceOptions())
        with patch("vector_studio.task_queue.trace_image", side_effect=_side_effect):
            q.start()
            task = q.wait_for(tid, timeout=10.0)

        assert task.status == "completed"
        assert call_count == 2

    def test_retry_exhausted_fails(self, tmp_path):
        img = tmp_path / "img.png"
        img.write_bytes(b"fake")
        out = tmp_path / "out.svg"

        q = TaskQueue(max_workers=1, max_retries=1)
        tid = q.add_task(img, out, TraceOptions())
        with patch("vector_studio.task_queue.trace_image", side_effect=RuntimeError("boom")):
            q.start()
            task = q.wait_for(tid, timeout=10.0)

        assert task.status == "failed"
        assert "boom" in task.error


class TestTaskQueueWait:
    def test_wait_for_timeout(self, tmp_path):
        q = TaskQueue()
        tid = q.add_task(tmp_path / "img.png", tmp_path / "out.svg", TraceOptions())
        # Do not start the queue, so the task never completes.
        with pytest.raises(TimeoutError):
            q.wait_for(tid, timeout=0.1)

    def test_wait_for_all(self, tmp_path):
        img = tmp_path / "img.png"
        img.write_bytes(b"fake")
        out = tmp_path / "out.svg"

        mock_result = TraceResult(
            input_path=img,
            svg_path=out,
            engine="python-vtracer",
            elapsed_seconds=0.5,
            stats={"paths": 3},
        )

        q = TaskQueue(max_workers=2)
        tid1 = q.add_task(img, out, TraceOptions())
        tid2 = q.add_task(img, out.with_name("out2.svg"), TraceOptions())

        with patch("vector_studio.task_queue.trace_image", return_value=mock_result):
            q.start()
            tasks = q.wait_for_all(timeout=5.0)

        assert len(tasks) == 2
        assert all(t.status == "completed" for t in tasks)


class TestTaskQueueReport:
    def test_export_report(self, tmp_path):
        img = tmp_path / "img.png"
        img.write_bytes(b"fake")
        out = tmp_path / "out.svg"

        mock_result = TraceResult(
            input_path=img,
            svg_path=out,
            engine="python-vtracer",
            elapsed_seconds=0.5,
            stats={"paths": 3},
        )

        q = TaskQueue(max_workers=1)
        q.add_task(img, out, TraceOptions())
        with patch("vector_studio.task_queue.trace_image", return_value=mock_result):
            q.start()
            q.wait_for_all(timeout=5.0)

        report_path = tmp_path / "report.csv"
        q.export_report(report_path)
        assert report_path.exists()
        text = report_path.read_text(encoding="utf-8")
        assert "task_id" in text
        assert "status" in text

    def test_export_report_empty(self, tmp_path):
        q = TaskQueue()
        report_path = tmp_path / "report.csv"
        q.export_report(report_path)
        assert report_path.exists()
        assert report_path.read_text(encoding="utf-8") == ""


class TestTaskQueuePauseResume:
    def test_pause_and_resume(self, tmp_path):
        img = tmp_path / "img.png"
        img.write_bytes(b"fake")
        out = tmp_path / "out.svg"

        mock_result = TraceResult(
            input_path=img,
            svg_path=out,
            engine="python-vtracer",
            elapsed_seconds=0.5,
            stats={"paths": 3},
        )

        q = TaskQueue(max_workers=1)
        tid = q.add_task(img, out, TraceOptions())
        q.pause()
        with patch("vector_studio.task_queue.trace_image", return_value=mock_result):
            q.start()
            # Paused, so task should not complete quickly.
            with pytest.raises(TimeoutError):
                q.wait_for(tid, timeout=0.3)
            q.resume()
            task = q.wait_for(tid, timeout=5.0)

        assert task.status == "completed"
