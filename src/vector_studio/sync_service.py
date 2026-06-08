from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _http_json_request(url: str, method: str = "GET", data: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
    """Perform a simple HTTP request and parse the JSON response."""
    body = json.dumps(data, ensure_ascii=False).encode("utf-8") if data else None
    req_headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    req = Request(url, data=body, headers=req_headers, method=method)
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _now_iso() -> str:
    """Return the current UTC timestamp as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# SyncClient
# ---------------------------------------------------------------------------


class SyncClient:
    """Client for synchronizing local data with a remote sync server.

    Parameters
    ----------
    server_url:
        Base URL of the sync server (default ``http://localhost:8000``).
    device_id:
        Unique identifier for this device.  Generated automatically when
        ``None``.
    """

    def __init__(self, server_url: str = "http://localhost:8000", device_id: str | None = None) -> None:
        self.server_url = server_url.rstrip("/")
        self.device_id = device_id or str(uuid.uuid4())
        self._device_info: dict[str, Any] = {
            "device_id": self.device_id,
            "platform": "python",
            "version": "1.0.0",
            "registered_at": _now_iso(),
        }
        self._registered = False

    def _ensure_registered(self) -> None:
        """Register the device with the server if not already done."""
        if self._registered:
            return
        try:
            _http_json_request(
                f"{self.server_url}/sync/register",
                method="POST",
                data={"device_id": self.device_id, "device_info": self._device_info},
            )
            self._registered = True
        except Exception as exc:
            logger.warning("Device registration failed: %s", exc)

    def _local_workspaces(self) -> list[dict[str, Any]]:
        """Load local workspaces from disk."""
        from .workspace import WorkspaceManager
        manager = WorkspaceManager()
        return manager.list_workspaces()

    def _local_presets(self) -> list[dict[str, Any]]:
        """Load local presets from disk."""
        from .preset_manager import list_user_presets
        raw = list_user_presets()
        return [{"name": k, **v} for k, v in raw.items()]

    def _local_config(self) -> dict[str, Any]:
        """Load local configuration from disk."""
        from .config import Config
        return Config.load().to_dict()

    def _local_history(self) -> list[dict[str, Any]]:
        """Load local conversion history from disk."""
        from .history import get_recent_tasks
        return get_recent_tasks(limit=100)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def sync_workspaces(self) -> list[dict[str, Any]]:
        """Pull remote workspaces and merge with local copies.

        Returns
        -------
        list[dict[str, Any]]
            The merged workspace list.
        """
        self._ensure_registered()
        local = self._local_workspaces()
        try:
            remote = _http_json_request(
                f"{self.server_url}/sync/pull",
                method="POST",
                data={"device_id": self.device_id, "data_type": "workspaces", "last_sync": "1970-01-01T00:00:00+00:00"},
            )
        except Exception as exc:
            logger.warning("Failed to pull workspaces: %s", exc)
            return local

        remote_data = remote.get("data", [])
        merged = self._merge_lists(local, remote_data, key="name")
        self._push_data("workspaces", merged)
        return merged

    def sync_presets(self) -> list[dict[str, Any]]:
        """Pull remote presets and merge with local copies.

        Returns
        -------
        list[dict[str, Any]]
            The merged preset list.
        """
        self._ensure_registered()
        local = self._local_presets()
        try:
            remote = _http_json_request(
                f"{self.server_url}/sync/pull",
                method="POST",
                data={"device_id": self.device_id, "data_type": "presets", "last_sync": "1970-01-01T00:00:00+00:00"},
            )
        except Exception as exc:
            logger.warning("Failed to pull presets: %s", exc)
            return local

        remote_data = remote.get("data", [])
        merged = self._merge_lists(local, remote_data, key="name")
        self._push_data("presets", merged)
        return merged

    def sync_config(self) -> dict[str, Any]:
        """Pull remote configuration and resolve conflicts.

        Returns
        -------
        dict[str, Any]
            The merged configuration dictionary.
        """
        self._ensure_registered()
        local = self._local_config()
        try:
            remote = _http_json_request(
                f"{self.server_url}/sync/pull",
                method="POST",
                data={"device_id": self.device_id, "data_type": "config", "last_sync": "1970-01-01T00:00:00+00:00"},
            )
        except Exception as exc:
            logger.warning("Failed to pull config: %s", exc)
            return local

        remote_data = remote.get("data", {})
        merged = self.resolve_conflict(local, remote_data)
        self._push_data("config", merged)
        return merged

    def sync_history(self) -> list[dict[str, Any]]:
        """Pull remote history and merge with local records.

        Returns
        -------
        list[dict[str, Any]]
            The merged history list (newest first).
        """
        self._ensure_registered()
        local = self._local_history()
        try:
            remote = _http_json_request(
                f"{self.server_url}/sync/pull",
                method="POST",
                data={"device_id": self.device_id, "data_type": "history", "last_sync": "1970-01-01T00:00:00+00:00"},
            )
        except Exception as exc:
            logger.warning("Failed to pull history: %s", exc)
            return local

        remote_data = remote.get("data", [])
        merged = self._merge_lists(local, remote_data, key="task_id")
        self._push_data("history", merged)
        return merged

    def resolve_conflict(self, local: dict[str, Any], remote: dict[str, Any]) -> dict[str, Any]:
        """Resolve a conflict between *local* and *remote* dictionaries.

        The dictionary with the newer ``updated_at`` / ``timestamp`` wins.
        If no timestamp is present, *local* wins.

        Parameters
        ----------
        local:
            Local data dictionary.
        remote:
            Remote data dictionary.

        Returns
        -------
        dict[str, Any]
            The winning dictionary.
        """
        local_ts = local.get("updated_at") or local.get("timestamp") or ""
        remote_ts = remote.get("updated_at") or remote.get("timestamp") or ""
        if remote_ts and remote_ts > local_ts:
            return dict(remote)
        return dict(local)

    def _merge_lists(
        self,
        local: list[dict[str, Any]],
        remote: list[dict[str, Any]],
        key: str,
    ) -> list[dict[str, Any]]:
        """Merge two lists of dictionaries keyed by *key*.

        Conflicts are resolved with :meth:`resolve_conflict`.
        """
        merged: dict[str, dict[str, Any]] = {}
        for item in local:
            k = item.get(key)
            if k is not None:
                merged[k] = dict(item)
        for item in remote:
            k = item.get(key)
            if k is None:
                continue
            if k in merged:
                merged[k] = self.resolve_conflict(merged[k], dict(item))
            else:
                merged[k] = dict(item)
        return list(merged.values())

    def _push_data(self, data_type: str, data: Any) -> bool:
        """Push *data* of *data_type* to the sync server."""
        try:
            _http_json_request(
                f"{self.server_url}/sync/push",
                method="POST",
                data={"device_id": self.device_id, "data_type": data_type, "data": data},
            )
            return True
        except Exception as exc:
            logger.warning("Failed to push %s: %s", data_type, exc)
            return False

    def push_all(self) -> dict[str, bool]:
        """Push all local data types to the server.

        Returns
        -------
        dict[str, bool]
            Success flags per data type.
        """
        return {
            "workspaces": self._push_data("workspaces", self._local_workspaces()),
            "presets": self._push_data("presets", self._local_presets()),
            "config": self._push_data("config", self._local_config()),
            "history": self._push_data("history", self._local_history()),
        }

    def get_sync_status(self) -> dict[str, Any]:
        """Query the server for the current sync status of this device."""
        self._ensure_registered()
        try:
            return _http_json_request(
                f"{self.server_url}/sync/status",
                method="POST",
                data={"device_id": self.device_id},
            )
        except Exception as exc:
            logger.warning("Failed to get sync status: %s", exc)
            return {"device_id": self.device_id, "status": "unknown", "error": str(exc)}


# ---------------------------------------------------------------------------
# SyncServer
# ---------------------------------------------------------------------------


@dataclass
class _DeviceRecord:
    """Internal record for a registered device."""

    device_id: str
    device_info: dict[str, Any]
    registered_at: str
    last_seen: str
    data_store: dict[str, dict[str, Any]] = field(default_factory=dict)


class SyncServer:
    """In-memory sync server that can be exposed via FastAPI or used
    standalone for testing.

    All data is stored in memory; persist to disk if durability is required.
    """

    def __init__(self) -> None:
        self._devices: dict[str, _DeviceRecord] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register_device(self, device_id: str, device_info: dict[str, Any]) -> str:
        """Register (or re-register) a device.

        Returns
        -------
        str
            The registered device ID.
        """
        now = _now_iso()
        with self._lock:
            if device_id in self._devices:
                self._devices[device_id].last_seen = now
                self._devices[device_id].device_info.update(device_info)
            else:
                self._devices[device_id] = _DeviceRecord(
                    device_id=device_id,
                    device_info=dict(device_info),
                    registered_at=now,
                    last_seen=now,
                )
        return device_id

    def push_sync_data(self, device_id: str, data_type: str, data: dict[str, Any]) -> bool:
        """Store sync data from a device.

        Returns
        -------
        bool
            ``True`` on success.
        """
        with self._lock:
            if device_id not in self._devices:
                raise ValueError(f"Device not registered: {device_id}")
            record = self._devices[device_id]
            record.data_store[data_type] = {
                "data": data,
                "pushed_at": _now_iso(),
            }
            record.last_seen = _now_iso()
        return True

    def pull_sync_data(self, device_id: str, data_type: str, last_sync: str) -> dict[str, Any]:
        """Retrieve sync data for a device.

        Parameters
        ----------
        device_id:
            The requesting device.
        data_type:
            One of ``workspaces``, ``presets``, ``config``, ``history``.
        last_sync:
            ISO-8601 timestamp of the client's last successful sync.

        Returns
        -------
        dict[str, Any]
            Dictionary with ``data`` and ``server_timestamp`` keys.
        """
        with self._lock:
            if device_id not in self._devices:
                raise ValueError(f"Device not registered: {device_id}")
            record = self._devices[device_id]
            entry = record.data_store.get(data_type, {})
            data = entry.get("data", {})
            pushed_at = entry.get("pushed_at", "")
            record.last_seen = _now_iso()
        return {
            "data": data,
            "server_timestamp": pushed_at or _now_iso(),
            "has_update": bool(pushed_at and pushed_at > last_sync),
        }

    def get_sync_status(self, device_id: str) -> dict[str, Any]:
        """Return the sync status for *device_id*."""
        with self._lock:
            if device_id not in self._devices:
                return {"registered": False, "device_id": device_id}
            record = self._devices[device_id]
            return {
                "registered": True,
                "device_id": device_id,
                "last_seen": record.last_seen,
                "registered_at": record.registered_at,
                "data_types": list(record.data_store.keys()),
            }

    def list_devices(self) -> list[dict[str, Any]]:
        """Return metadata for all registered devices."""
        with self._lock:
            return [
                {
                    "device_id": d.device_id,
                    "registered_at": d.registered_at,
                    "last_seen": d.last_seen,
                    "data_types": list(d.data_store.keys()),
                }
                for d in self._devices.values()
            ]

    def unregister_device(self, device_id: str) -> bool:
        """Remove a device and all its data."""
        with self._lock:
            return self._devices.pop(device_id, None) is not None
