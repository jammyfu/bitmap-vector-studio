"""Real-time collaboration module for Bitmap Vector Studio.

Provides room-based collaborative editing with operation logging,
optimistic locking, and WebSocket broadcasting.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

try:
    from fastapi import WebSocket, WebSocketDisconnect
    _HAS_FASTAPI = True
except ImportError:  # pragma: no cover
    WebSocket = Any  # type: ignore[misc,assignment]
    WebSocketDisconnect = Exception  # type: ignore[misc,assignment]
    _HAS_FASTAPI = False


@dataclass
class Operation:
    """Represents a single collaborative operation.

    Attributes
    ----------
    op_id:
        Unique identifier for the operation.
    client_id:
        Identifier of the client that submitted the operation.
    timestamp:
        Unix timestamp when the operation was created.
    type:
        Operation type. One of ``param_change``, ``preview_update``,
        ``file_upload``, ``convert``.
    data:
        Arbitrary payload specific to the operation type.
    version:
        Optimistic-lock version number for conflict resolution.
    """

    op_id: str
    client_id: str
    timestamp: float
    type: str
    data: dict[str, Any]
    version: int

    def to_dict(self) -> dict[str, Any]:
        """Serialize the operation to a plain dictionary."""
        return {
            "op_id": self.op_id,
            "client_id": self.client_id,
            "timestamp": self.timestamp,
            "type": self.type,
            "data": self.data,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Operation":
        """Deserialize an operation from a plain dictionary."""
        return cls(
            op_id=raw["op_id"],
            client_id=raw["client_id"],
            timestamp=raw["timestamp"],
            type=raw["type"],
            data=raw.get("data", {}),
            version=raw.get("version", 1),
        )


class CollabRoom:
    """A single collaboration room.

    Manages connected WebSocket clients, shared state, and an ordered
    operation log that can be replayed for late-joining clients.
    """

    def __init__(self, room_id: str, owner: str, created_at: str | None = None) -> None:
        """Create a new collaboration room.

        Parameters
        ----------
        room_id:
            Unique room identifier.
        owner:
            User identifier that owns the room.
        created_at:
            ISO-formatted creation time. Defaults to the current UTC time.
        """
        self.room_id: str = room_id
        self.owner: str = owner
        self.created_at: str = created_at or self._now_iso()
        self.clients: dict[str, WebSocket] = {}
        self.state: dict[str, Any] = {
            "params": {},
            "preview": None,
            "files": [],
        }
        self.operation_log: list[Operation] = []
        self._lock = asyncio.Lock()
        self._next_version = 1

    @staticmethod
    def _now_iso() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()

    async def broadcast(
        self,
        message: dict[str, Any],
        exclude: str | None = None,
    ) -> None:
        """Broadcast a JSON message to all connected clients.

        Parameters
        ----------
        message:
            Dictionary to send as JSON.
        exclude:
            Optional ``client_id`` to skip (e.g. the sender).
        """
        dead_clients: list[str] = []
        for client_id, ws in self.clients.items():
            if exclude is not None and client_id == exclude:
                continue
            try:
                if _HAS_FASTAPI:
                    await ws.send_json(message)
            except Exception:  # pragma: no cover
                dead_clients.append(client_id)
        for cid in dead_clients:
            self.clients.pop(cid, None)

    async def apply_operation(self, op: Operation) -> dict[str, Any]:
        """Apply an operation to the room state and append it to the log.

        The method validates optimistic-lock versioning, updates the
        in-memory state according to the operation type, and broadcasts
        the accepted operation to all other clients.

        Parameters
        ----------
        op:
            The operation to apply.

        Returns
        -------
        dict
            Confirmation payload containing ``op_id``, ``version``,
            and the updated room state snapshot.
        """
        async with self._lock:
            if op.version != self._next_version:
                return {
                    "op_id": op.op_id,
                    "status": "rejected",
                    "reason": "version mismatch",
                    "expected_version": self._next_version,
                }

            # Update state based on operation type
            if op.type == "param_change":
                params = op.data.get("params", {})
                self.state["params"].update(params)
            elif op.type == "preview_update":
                self.state["preview"] = op.data.get("preview")
            elif op.type == "file_upload":
                file_info = op.data.get("file", {})
                if file_info:
                    self.state["files"].append(file_info)
            elif op.type == "convert":
                result = op.data.get("result", {})
                self.state["last_convert"] = result

            self.operation_log.append(op)
            self._next_version += 1

        # Notify other clients outside the lock
        await self.broadcast(
            {
                "event": "operation_applied",
                "op": op.to_dict(),
                "room_id": self.room_id,
            },
            exclude=op.client_id,
        )

        return {
            "op_id": op.op_id,
            "status": "accepted",
            "version": op.version,
            "state": self.get_state_snapshot(),
        }

    def get_state_snapshot(self) -> dict[str, Any]:
        """Return a snapshot of the current room state.

        Returns
        -------
        dict
            Deep copy of the room state dictionary.
        """
        import copy
        return {
            "room_id": self.room_id,
            "owner": self.owner,
            "created_at": self.created_at,
            "params": copy.deepcopy(self.state.get("params", {})),
            "preview": self.state.get("preview"),
            "files": copy.deepcopy(self.state.get("files", [])),
            "last_convert": copy.deepcopy(self.state.get("last_convert", {})),
            "client_count": len(self.clients),
            "operation_count": len(self.operation_log),
            "next_version": self._next_version,
        }

    def get_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return the most recent operations from the log.

        Parameters
        ----------
        limit:
            Maximum number of operations to return.

        Returns
        -------
        list[dict]
            Serialized operations, newest first.
        """
        recent = self.operation_log[-limit:]
        return [op.to_dict() for op in recent]

    async def add_client(self, client_id: str, websocket: WebSocket) -> None:
        """Register a new WebSocket client in the room.

        Parameters
        ----------
        client_id:
            Unique client identifier.
        websocket:
            The FastAPI WebSocket instance.
        """
        self.clients[client_id] = websocket
        await self.broadcast(
            {
                "event": "client_joined",
                "client_id": client_id,
                "room_id": self.room_id,
                "client_count": len(self.clients),
            }
        )

    async def remove_client(self, client_id: str) -> None:
        """Remove a client and notify remaining participants.

        Parameters
        ----------
        client_id:
            The client to remove.
        """
        self.clients.pop(client_id, None)
        await self.broadcast(
            {
                "event": "client_left",
                "client_id": client_id,
                "room_id": self.room_id,
                "client_count": len(self.clients),
            }
        )


class CollabManager:
    """Global manager for all collaboration rooms.

    Provides thread-safe (async-safe) creation, lookup, and destruction
    of :class:`CollabRoom` instances.
    """

    def __init__(self) -> None:
        self.rooms: dict[str, CollabRoom] = {}
        self._lock = asyncio.Lock()

    async def create_room(self, owner: str) -> str:
        """Create a new collaboration room.

        Parameters
        ----------
        owner:
            User identifier that will own the room.

        Returns
        -------
        str
            The generated room identifier.
        """
        room_id = str(uuid.uuid4())[:8]
        async with self._lock:
            self.rooms[room_id] = CollabRoom(room_id=room_id, owner=owner)
        return room_id

    async def join_room(
        self,
        room_id: str,
        client_id: str,
        websocket: WebSocket,
    ) -> CollabRoom:
        """Add a WebSocket client to an existing room.

        Parameters
        ----------
        room_id:
            Target room identifier.
        client_id:
            Client identifier.
        websocket:
            FastAPI WebSocket instance.

        Returns
        -------
        CollabRoom
            The room instance.

        Raises
        ------
        KeyError
            If the room does not exist.
        """
        async with self._lock:
            room = self.rooms[room_id]
        await room.add_client(client_id, websocket)
        return room

    async def leave_room(self, room_id: str, client_id: str) -> None:
        """Remove a client from a room.

        If the room becomes empty it is **not** automatically destroyed
        so that the operation log and state remain available for re-joins.

        Parameters
        ----------
        room_id:
            Room identifier.
        client_id:
            Client to remove.
        """
        async with self._lock:
            room = self.rooms.get(room_id)
        if room is None:
            return
        await room.remove_client(client_id)

    def get_room(self, room_id: str) -> CollabRoom | None:
        """Look up a room by identifier.

        Returns
        -------
        CollabRoom | None
            The room if it exists, otherwise ``None``.
        """
        return self.rooms.get(room_id)

    def list_rooms(self) -> list[dict[str, Any]]:
        """List metadata for all active rooms.

        Returns
        -------
        list[dict]
            One dictionary per room with ``room_id``, ``owner``,
            ``created_at``, and ``client_count``.
        """
        return [
            {
                "room_id": room.room_id,
                "owner": room.owner,
                "created_at": room.created_at,
                "client_count": len(room.clients),
                "operation_count": len(room.operation_log),
            }
            for room in self.rooms.values()
        ]

    async def delete_room(self, room_id: str) -> bool:
        """Permanently remove a room.

        Parameters
        ----------
        room_id:
            Room to delete.

        Returns
        -------
        bool
            ``True`` if the room existed and was removed.
        """
        async with self._lock:
            return self.rooms.pop(room_id, None) is not None


# Global singleton used by the API layer.
_collab_manager: CollabManager | None = None
_manager_lock = asyncio.Lock()


async def get_collab_manager() -> CollabManager:
    """Return the global :class:`CollabManager` singleton."""
    global _collab_manager
    if _collab_manager is None:
        async with _manager_lock:
            if _collab_manager is None:
                _collab_manager = CollabManager()
    return _collab_manager
