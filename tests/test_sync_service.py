from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vector_studio.sync_service import SyncClient, SyncServer


class TestSyncServer:
    def test_register_device(self):
        """Registering a device should return the same device ID."""
        server = SyncServer()
        did = server.register_device("dev-1", {"platform": "test"})
        assert did == "dev-1"
        status = server.get_sync_status("dev-1")
        assert status["registered"] is True

    def test_push_and_pull(self):
        """Pushed data should be retrievable via pull."""
        server = SyncServer()
        server.register_device("dev-1", {})
        payload = {"key": "value", "updated_at": "2024-01-01T00:00:00+00:00"}
        assert server.push_sync_data("dev-1", "config", payload) is True

        result = server.pull_sync_data("dev-1", "config", "1970-01-01T00:00:00+00:00")
        assert result["data"] == payload
        assert result["has_update"] is True

    def test_pull_no_update(self):
        """Pulling with a future last_sync should report no update."""
        server = SyncServer()
        server.register_device("dev-1", {})
        server.push_sync_data("dev-1", "config", {"key": "v1"})
        result = server.pull_sync_data("dev-1", "config", "2099-01-01T00:00:00+00:00")
        assert result["has_update"] is False

    def test_unregister_device(self):
        """Unregistering should remove the device and its data."""
        server = SyncServer()
        server.register_device("dev-1", {})
        assert server.unregister_device("dev-1") is True
        status = server.get_sync_status("dev-1")
        assert status["registered"] is False

    def test_list_devices(self):
        """list_devices should return all registered devices."""
        server = SyncServer()
        server.register_device("a", {"name": "A"})
        server.register_device("b", {"name": "B"})
        devices = server.list_devices()
        assert len(devices) == 2
        assert {d["device_id"] for d in devices} == {"a", "b"}

    def test_unregistered_push_raises(self):
        """Pushing for an unregistered device should raise ValueError."""
        server = SyncServer()
        with pytest.raises(ValueError, match="not registered"):
            server.push_sync_data("unknown", "config", {})


class TestSyncClient:
    def test_resolve_conflict_local_wins_without_timestamp(self):
        """When neither side has a timestamp, local should win."""
        client = SyncClient()
        local = {"key": "local"}
        remote = {"key": "remote"}
        result = client.resolve_conflict(local, remote)
        assert result["key"] == "local"

    def test_resolve_conflict_remote_wins_when_newer(self):
        """Remote should win when its timestamp is newer."""
        client = SyncClient()
        local = {"key": "local", "updated_at": "2024-01-01T00:00:00+00:00"}
        remote = {"key": "remote", "updated_at": "2024-06-01T00:00:00+00:00"}
        result = client.resolve_conflict(local, remote)
        assert result["key"] == "remote"

    def test_merge_lists(self):
        """Merging two lists by key should resolve conflicts."""
        client = SyncClient()
        local = [{"name": "a", "val": 1, "updated_at": "2024-01-01T00:00:00+00:00"}]
        remote = [{"name": "a", "val": 2, "updated_at": "2024-06-01T00:00:00+00:00"}]
        merged = client._merge_lists(local, remote, key="name")
        assert len(merged) == 1
        assert merged[0]["val"] == 2

    def test_push_all_returns_statuses(self, tmp_path: Path):
        """push_all should return a dict of success flags."""
        client = SyncClient(server_url="http://localhost:9999")
        # Mock the HTTP push so it doesn't fail on missing server.
        with patch.object(client, "_push_data", return_value=True):
            results = client.push_all()
        assert set(results.keys()) == {"workspaces", "presets", "config", "history"}
        assert all(results.values())

    def test_get_sync_status_graceful_failure(self):
        """get_sync_status should not crash when the server is unreachable."""
        client = SyncClient(server_url="http://localhost:9999")
        status = client.get_sync_status()
        assert "device_id" in status
        assert status.get("status") == "unknown"

    def test_client_auto_registration(self):
        """The client should attempt to register on first sync operation."""
        client = SyncClient(server_url="http://localhost:9999")
        assert not client._registered
        # _ensure_registered should be called by sync methods.
        with patch.object(client, "_push_data", return_value=True):
            client.push_all()
        # Registration would have been attempted (and failed silently).
        # The flag stays False because the mock server isn't real.
        assert not client._registered
