from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from vector_studio.models import TraceOptions
from vector_studio.workspace import (
    CrashRecovery,
    Workspace,
    WorkspaceManager,
    _crash_file_path,
)


class TestWorkspaceSerialization:
    def test_workspace_to_dict(self):
        ws = Workspace(
            open_files=["a.png", "b.jpg"],
            current_preset="logo",
            current_options=TraceOptions(colormode="binary"),
            sidebar_width=300,
            preview_mode="full",
        )
        d = ws.to_dict()
        assert d["open_files"] == ["a.png", "b.jpg"]
        assert d["current_preset"] == "logo"
        assert d["current_options"]["colormode"] == "binary"
        assert d["sidebar_width"] == 300
        assert d["preview_mode"] == "full"

    def test_workspace_from_dict(self):
        d = {
            "open_files": ["x.png"],
            "current_preset": "photo",
            "current_options": {"colormode": "color", "filter_speckle": 8},
            "sidebar_width": 200,
            "preview_mode": "split",
            "timestamp": "2024-01-01T00:00:00+00:00",
        }
        ws = Workspace.from_dict(d)
        assert ws.open_files == ["x.png"]
        assert ws.current_preset == "photo"
        assert ws.current_options.filter_speckle == 8
        assert ws.sidebar_width == 200

    def test_workspace_from_dict_defaults(self):
        ws = Workspace.from_dict({})
        assert ws.open_files == []
        assert ws.current_preset == "poster"
        assert ws.current_options == TraceOptions()


class TestWorkspaceManagerSaveLoad:
    def test_save_and_load(self, tmp_path):
        mgr = WorkspaceManager(workspace_dir=tmp_path)
        ws = Workspace(open_files=["a.png"], current_preset="bw")
        path = mgr.save(ws, name="test_ws")
        assert path.exists()

        loaded = mgr.load("test_ws")
        assert loaded is not None
        assert loaded.open_files == ["a.png"]
        assert loaded.current_preset == "bw"

    def test_load_missing_returns_none(self, tmp_path):
        mgr = WorkspaceManager(workspace_dir=tmp_path)
        assert mgr.load("missing") is None

    def test_auto_naming_with_timestamp(self, tmp_path):
        mgr = WorkspaceManager(workspace_dir=tmp_path)
        ws = Workspace()
        path = mgr.save(ws)
        assert path.exists()
        assert path.suffix == ".json"

    def test_list_workspaces(self, tmp_path):
        mgr = WorkspaceManager(workspace_dir=tmp_path)
        mgr.save(Workspace(), "ws1")
        mgr.save(Workspace(), "ws2")
        items = mgr.list_workspaces()
        assert len(items) == 2
        names = {i["name"] for i in items}
        assert names == {"ws1", "ws2"}

    def test_delete_workspace(self, tmp_path):
        mgr = WorkspaceManager(workspace_dir=tmp_path)
        mgr.save(Workspace(), "del_me")
        assert mgr.delete("del_me") is True
        assert mgr.load("del_me") is None
        assert mgr.delete("del_me") is False


class TestWorkspaceManagerAutoSave:
    def test_auto_save_creates_timer(self, tmp_path):
        mgr = WorkspaceManager(workspace_dir=tmp_path)
        ws = Workspace()
        mgr.auto_save_current(ws, interval=1)
        assert mgr._auto_save_timer is not None
        mgr.stop_auto_save()

    def test_auto_save_writes_file(self, tmp_path):
        mgr = WorkspaceManager(workspace_dir=tmp_path)
        ws = Workspace(open_files=["a.png"])
        mgr.auto_save_current(ws, interval=1)
        time.sleep(1.5)
        mgr.stop_auto_save()
        auto = mgr.load("auto_save")
        assert auto is not None
        assert auto.open_files == ["a.png"]

    def test_restore_last_prefers_auto_save(self, tmp_path):
        mgr = WorkspaceManager(workspace_dir=tmp_path)
        mgr.save(Workspace(open_files=["manual.png"]), "manual")
        mgr.save(Workspace(open_files=["auto.png"]), "auto_save")
        last = mgr.restore_last()
        assert last is not None
        assert last.open_files == ["auto.png"]

    def test_restore_last_falls_back_to_newest(self, tmp_path):
        mgr = WorkspaceManager(workspace_dir=tmp_path)
        mgr.save(Workspace(open_files=["old.png"]), "old")
        time.sleep(0.1)
        mgr.save(Workspace(open_files=["new.png"]), "new")
        last = mgr.restore_last()
        assert last is not None
        assert last.open_files == ["new.png"]

    def test_restore_last_empty_returns_none(self, tmp_path):
        mgr = WorkspaceManager(workspace_dir=tmp_path)
        assert mgr.restore_last() is None


class TestCrashRecovery:
    def test_save_and_check_crash_recovery(self, tmp_path, monkeypatch):
        crash_path = tmp_path / "crash.json"
        monkeypatch.setattr(
            "vector_studio.workspace._crash_file_path", lambda: crash_path
        )
        recovery = CrashRecovery()
        ws = Workspace(open_files=["crash.png"])
        recovery.save_crash_state(ws)

        loaded = recovery.check_crash_recovery()
        assert loaded is not None
        assert loaded.open_files == ["crash.png"]

    def test_check_crash_recovery_none_when_missing(self, tmp_path, monkeypatch):
        crash_path = tmp_path / "crash.json"
        monkeypatch.setattr(
            "vector_studio.workspace._crash_file_path", lambda: crash_path
        )
        recovery = CrashRecovery()
        assert recovery.check_crash_recovery() is None

    def test_clear_crash_state(self, tmp_path, monkeypatch):
        crash_path = tmp_path / "crash.json"
        monkeypatch.setattr(
            "vector_studio.workspace._crash_file_path", lambda: crash_path
        )
        recovery = CrashRecovery()
        recovery.save_crash_state(Workspace())
        assert crash_path.exists()
        assert recovery.clear_crash_state() is True
        assert not crash_path.exists()
        assert recovery.clear_crash_state() is False

    def test_clear_crash_state_idempotent(self, tmp_path, monkeypatch):
        crash_path = tmp_path / "crash.json"
        monkeypatch.setattr(
            "vector_studio.workspace._crash_file_path", lambda: crash_path
        )
        recovery = CrashRecovery()
        assert recovery.clear_crash_state() is False
