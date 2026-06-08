from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vector_studio.checkpoint import CheckpointManager, _deserialize_task, _serialize_task
from vector_studio.models import TraceOptions, TraceResult
from vector_studio.task_queue import ConversionTask


class TestCheckpointManagerSaveLoad:
    def test_save_and_load_roundtrip(self, tmp_path):
        mgr = CheckpointManager(checkpoint_dir=tmp_path)
        task = ConversionTask(
            task_id="t1",
            input_path=Path("in.png"),
            output_path=Path("out.svg"),
            options=TraceOptions(colormode="binary"),
            status="pending",
        )
        path = mgr.save_checkpoint("batch-1", [task])
        assert path.exists()

        loaded = mgr.load_checkpoint("batch-1")
        assert loaded is not None
        assert len(loaded) == 1
        assert loaded[0].task_id == "t1"
        assert loaded[0].options.colormode == "binary"

    def test_load_missing_returns_none(self, tmp_path):
        mgr = CheckpointManager(checkpoint_dir=tmp_path)
        assert mgr.load_checkpoint("nonexistent") is None

    def test_save_overwrites_existing(self, tmp_path):
        mgr = CheckpointManager(checkpoint_dir=tmp_path)
        mgr.save_checkpoint("q1", [ConversionTask("t1", Path("a.png"), Path("a.svg"), TraceOptions())])
        mgr.save_checkpoint("q1", [ConversionTask("t2", Path("b.png"), Path("b.svg"), TraceOptions())])
        loaded = mgr.load_checkpoint("q1")
        assert loaded is not None
        assert len(loaded) == 1
        assert loaded[0].task_id == "t2"


class TestCheckpointManagerListDelete:
    def test_list_checkpoints(self, tmp_path):
        mgr = CheckpointManager(checkpoint_dir=tmp_path)
        mgr.save_checkpoint("a", [ConversionTask("t1", Path("a.png"), Path("a.svg"), TraceOptions())])
        mgr.save_checkpoint("b", [ConversionTask("t2", Path("b.png"), Path("b.svg"), TraceOptions())])
        items = mgr.list_checkpoints()
        assert len(items) == 2
        ids = {i["queue_id"] for i in items}
        assert ids == {"a", "b"}

    def test_delete_checkpoint(self, tmp_path):
        mgr = CheckpointManager(checkpoint_dir=tmp_path)
        mgr.save_checkpoint("del", [ConversionTask("t1", Path("a.png"), Path("a.svg"), TraceOptions())])
        assert mgr.delete_checkpoint("del") is True
        assert mgr.load_checkpoint("del") is None
        assert mgr.delete_checkpoint("del") is False

    def test_list_skips_corrupt_files(self, tmp_path):
        mgr = CheckpointManager(checkpoint_dir=tmp_path)
        (tmp_path / "bad.json").write_text("not json")
        items = mgr.list_checkpoints()
        assert items == []


class TestCheckpointManagerAutoSave:
    def test_auto_save_creates_timer(self, tmp_path):
        mgr = CheckpointManager(checkpoint_dir=tmp_path)
        tasks = [ConversionTask("t1", Path("a.png"), Path("a.svg"), TraceOptions())]
        mgr.auto_save("q1", tasks, interval=1)
        assert "q1" in mgr._auto_save_timers
        mgr.stop_auto_save("q1")

    def test_auto_save_writes_file(self, tmp_path):
        mgr = CheckpointManager(checkpoint_dir=tmp_path)
        tasks = [ConversionTask("t1", Path("a.png"), Path("a.svg"), TraceOptions())]
        mgr.auto_save("q1", tasks, interval=1)
        time.sleep(1.5)
        loaded = mgr.load_checkpoint("q1")
        mgr.stop_auto_save("q1")
        assert loaded is not None
        assert len(loaded) == 1

    def test_stop_all_auto_save(self, tmp_path):
        mgr = CheckpointManager(checkpoint_dir=tmp_path)
        mgr.auto_save("q1", [], interval=10)
        mgr.auto_save("q2", [], interval=10)
        mgr.stop_all_auto_save()
        assert mgr._auto_save_timers == {}


class TestSerializeDeserialize:
    def test_serialize_deserialize_with_result(self):
        task = ConversionTask(
            task_id="t1",
            input_path=Path("in.png"),
            output_path=Path("out.svg"),
            options=TraceOptions(),
            status="completed",
            result=TraceResult(
                input_path=Path("in.png"),
                svg_path=Path("out.svg"),
                engine="vtracer",
                elapsed_seconds=1.2,
                stats={"paths": 5},
            ),
        )
        data = _serialize_task(task)
        restored = _deserialize_task(data)
        assert restored.task_id == "t1"
        assert restored.status == "completed"
        assert restored.result is not None
        assert restored.result.engine == "vtracer"

    def test_deserialize_ignores_unknown_option_keys(self):
        data = {
            "task_id": "t1",
            "input_path": "a.png",
            "output_path": "a.svg",
            "options": {"colormode": "color", "unknown_key": 123},
            "status": "pending",
        }
        task = _deserialize_task(data)
        assert task.options.colormode == "color"


class TestCheckpointManagerConcurrency:
    def test_save_is_thread_safe(self, tmp_path):
        mgr = CheckpointManager(checkpoint_dir=tmp_path)
        tasks = [ConversionTask("t1", Path("a.png"), Path("a.svg"), TraceOptions())]
        # Multiple rapid saves should not corrupt the file.
        for _ in range(10):
            mgr.save_checkpoint("race", tasks)
        loaded = mgr.load_checkpoint("race")
        assert loaded is not None
        assert len(loaded) == 1
