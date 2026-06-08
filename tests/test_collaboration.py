from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from vector_studio.api import app, _cleanup_api_temp
from vector_studio.collaboration import (
    CollabManager,
    CollabRoom,
    Operation,
    get_collab_manager,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_collab_state():
    """Reset the global collaboration manager between tests."""
    import vector_studio.api as api_module
    import vector_studio.collaboration as collab_module

    # Reset global manager
    collab_module._collab_manager = None
    api_module._task_queue = None
    yield
    _cleanup_api_temp()
    collab_module._collab_manager = None
    api_module._task_queue = None


class MockWebSocket:
    """In-memory mock of a FastAPI WebSocket for testing."""

    def __init__(self):
        self.sent_messages: list[dict] = []
        self.closed = False
        self.close_code = None
        self.received_messages: list[dict] = []
        self._receive_iter = None

    async def accept(self):
        pass

    async def send_json(self, data: dict):
        self.sent_messages.append(data)

    async def receive_json(self):
        if self._receive_iter is None:
            self._receive_iter = iter(self.received_messages)
        try:
            return next(self._receive_iter)
        except StopIteration:
            raise ConnectionResetError("Mock disconnect")

    async def close(self, code: int = 1000):
        self.closed = True
        self.close_code = code

    def queue_message(self, data: dict):
        self.received_messages.append(data)


class _MockDisconnect(Exception):
    """Custom exception to simulate a WebSocket disconnect in tests."""
    pass


class TestCollabRoomUnit:
    def test_room_initial_state(self):
        room = CollabRoom(room_id="r1", owner="alice")
        assert room.room_id == "r1"
        assert room.owner == "alice"
        assert room.clients == {}
        assert room.state["params"] == {}
        assert room.state["preview"] is None
        assert room.state["files"] == []
        assert room.operation_log == []

    def test_broadcast_excludes_sender(self):
        room = CollabRoom(room_id="r1", owner="alice")
        ws_a = MockWebSocket()
        ws_b = MockWebSocket()
        room.clients["a"] = ws_a
        room.clients["b"] = ws_b

        asyncio.run(room.broadcast({"msg": "hello"}, exclude="a"))
        assert len(ws_a.sent_messages) == 0
        assert len(ws_b.sent_messages) == 1
        assert ws_b.sent_messages[0]["msg"] == "hello"

    def test_apply_operation_param_change(self):
        room = CollabRoom(room_id="r1", owner="alice")
        ws = MockWebSocket()
        room.clients["a"] = ws

        op = Operation(
            op_id="op1",
            client_id="a",
            timestamp=1.0,
            type="param_change",
            data={"params": {"filter_speckle": 8}},
            version=1,
        )
        result = asyncio.run(room.apply_operation(op))
        assert result["status"] == "accepted"
        assert result["version"] == 1
        assert room.state["params"]["filter_speckle"] == 8
        assert len(room.operation_log) == 1

    def test_apply_operation_version_rejection(self):
        room = CollabRoom(room_id="r1", owner="alice")
        # Seed with one operation so next_version becomes 2
        op1 = Operation(
            op_id="op1",
            client_id="a",
            timestamp=1.0,
            type="param_change",
            data={"params": {}},
            version=1,
        )
        asyncio.run(room.apply_operation(op1))

        op2 = Operation(
            op_id="op2",
            client_id="a",
            timestamp=2.0,
            type="param_change",
            data={"params": {}},
            version=1,  # stale version
        )
        result = asyncio.run(room.apply_operation(op2))
        assert result["status"] == "rejected"
        assert result["reason"] == "version mismatch"
        assert result["expected_version"] == 2

    def test_add_and_remove_client(self):
        room = CollabRoom(room_id="r1", owner="alice")
        ws = MockWebSocket()
        asyncio.run(room.add_client("c1", ws))
        assert "c1" in room.clients
        assert any(m.get("event") == "client_joined" for m in ws.sent_messages)

        asyncio.run(room.remove_client("c1"))
        assert "c1" not in room.clients

    def test_get_state_snapshot(self):
        room = CollabRoom(room_id="r1", owner="alice", created_at="2024-01-01T00:00:00")
        room.state["params"] = {"preset": "logo"}
        room.state["files"] = [{"name": "a.svg"}]
        snap = room.get_state_snapshot()
        assert snap["room_id"] == "r1"
        assert snap["params"]["preset"] == "logo"
        assert snap["files"][0]["name"] == "a.svg"
        assert snap["client_count"] == 0
        assert snap["operation_count"] == 0

    def test_get_history(self):
        room = CollabRoom(room_id="r1", owner="alice")
        for i in range(5):
            room.operation_log.append(
                Operation(
                    op_id=f"op{i}",
                    client_id="a",
                    timestamp=float(i),
                    type="param_change",
                    data={},
                    version=i + 1,
                )
            )
        hist = room.get_history(limit=3)
        assert len(hist) == 3
        assert hist[0]["op_id"] == "op2"
        assert hist[-1]["op_id"] == "op4"


class TestCollabManagerUnit:
    def test_create_room(self):
        mgr = CollabManager()
        rid = asyncio.run(mgr.create_room("bob"))
        assert rid in mgr.rooms
        assert mgr.rooms[rid].owner == "bob"

    def test_join_and_leave_room(self):
        mgr = CollabManager()
        rid = asyncio.run(mgr.create_room("bob"))
        ws = MockWebSocket()
        room = asyncio.run(mgr.join_room(rid, "c1", ws))
        assert "c1" in room.clients
        asyncio.run(mgr.leave_room(rid, "c1"))
        assert "c1" not in room.clients

    def test_get_room_missing(self):
        mgr = CollabManager()
        assert mgr.get_room("nonexistent") is None

    def test_list_rooms(self):
        mgr = CollabManager()
        # Synchronously populate for simplicity
        room = CollabRoom(room_id="r1", owner="alice")
        mgr.rooms["r1"] = room
        rooms = mgr.list_rooms()
        assert len(rooms) == 1
        assert rooms[0]["room_id"] == "r1"

    def test_delete_room(self):
        mgr = CollabManager()
        rid = asyncio.run(mgr.create_room("alice"))
        assert asyncio.run(mgr.delete_room(rid)) is True
        assert asyncio.run(mgr.delete_room(rid)) is False


class TestCollabApiEndpoints:
    def test_create_room_http(self):
        response = client.post("/collab/rooms?owner=alice")
        assert response.status_code == 200
        data = response.json()
        assert "room_id" in data
        assert data["owner"] == "alice"
        assert "created_at" in data

    def test_get_room_state(self):
        # Create a room first
        resp = client.post("/collab/rooms?owner=bob")
        rid = resp.json()["room_id"]

        response = client.get(f"/collab/rooms/{rid}")
        assert response.status_code == 200
        data = response.json()
        assert data["room_id"] == rid
        assert data["owner"] == "bob"
        assert data["client_count"] == 0

    def test_get_room_state_not_found(self):
        response = client.get("/collab/rooms/does-not-exist")
        assert response.status_code == 404
        assert "Room not found" in response.json()["detail"]

    def test_submit_operation(self):
        resp = client.post("/collab/rooms?owner=alice")
        rid = resp.json()["room_id"]

        payload = {
            "client_id": "cli1",
            "type": "param_change",
            "data": {"params": {"color_precision": 6}},
            "version": 1,
        }
        response = client.post(f"/collab/rooms/{rid}/operations", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        assert data["version"] == 1
        assert data["state"]["params"]["color_precision"] == 6

    def test_submit_operation_room_not_found(self):
        payload = {
            "client_id": "cli1",
            "type": "param_change",
            "data": {},
            "version": 1,
        }
        response = client.post("/collab/rooms/missing/operations", json=payload)
        assert response.status_code == 404

    def test_get_operation_history(self):
        resp = client.post("/collab/rooms?owner=alice")
        rid = resp.json()["room_id"]

        # Submit a few operations
        for i in range(3):
            client.post(
                f"/collab/rooms/{rid}/operations",
                json={
                    "client_id": "c1",
                    "type": "param_change",
                    "data": {"params": {"x": i}},
                    "version": i + 1,
                },
            )

        response = client.get(f"/collab/rooms/{rid}/history?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["operations"]) == 2

    def test_list_rooms_endpoint(self):
        client.post("/collab/rooms?owner=alice")
        client.post("/collab/rooms?owner=bob")
        response = client.get("/collab/rooms")
        assert response.status_code == 200
        data = response.json()
        assert len(data["rooms"]) >= 2


class TestCollabWebSocket:
    def test_websocket_join_and_state(self):
        mgr = asyncio.run(get_collab_manager())
        rid = asyncio.run(mgr.create_room("alice"))
        room = mgr.get_room(rid)
        assert room is not None

        ws = MockWebSocket()
        ws.queue_message({"event": "join", "client_id": "c1"})
        ws.queue_message({"event": "ping"})

        from vector_studio.api import collab_websocket
        try:
            asyncio.run(collab_websocket(ws, rid))
        except ConnectionResetError:
            pass

        # Should have received joined + pong
        events = [m.get("event") for m in ws.sent_messages]
        assert "joined" in events
        assert "pong" in events

    def test_websocket_operation(self):
        mgr = asyncio.run(get_collab_manager())
        rid = asyncio.run(mgr.create_room("alice"))
        room = mgr.get_room(rid)
        assert room is not None

        ws = MockWebSocket()
        ws.queue_message({"event": "join", "client_id": "c1"})
        ws.queue_message({
            "event": "operation",
            "op": {
                "type": "param_change",
                "data": {"params": {"preset": "logo"}},
                "version": 1,
            },
        })

        from vector_studio.api import collab_websocket
        try:
            asyncio.run(collab_websocket(ws, rid))
        except ConnectionResetError:
            pass

        # Find operation_result event
        op_results = [m for m in ws.sent_messages if m.get("event") == "operation_result"]
        assert len(op_results) == 1
        assert op_results[0]["result"]["status"] == "accepted"
        assert room.state["params"]["preset"] == "logo"

    def test_websocket_room_not_found(self):
        ws = MockWebSocket()
        ws.queue_message({"event": "join", "client_id": "c1"})

        from vector_studio.api import collab_websocket
        try:
            asyncio.run(collab_websocket(ws, "missing-room"))
        except ConnectionResetError:
            pass

        assert any(m.get("event") == "error" and "Room not found" in m.get("detail", "") for m in ws.sent_messages)
        assert ws.closed is True

    def test_websocket_operation_before_join(self):
        mgr = asyncio.run(get_collab_manager())
        rid = asyncio.run(mgr.create_room("alice"))

        ws = MockWebSocket()
        ws.queue_message({
            "event": "operation",
            "op": {"type": "param_change", "data": {}, "version": 1},
        })

        from vector_studio.api import collab_websocket
        try:
            asyncio.run(collab_websocket(ws, rid))
        except ConnectionResetError:
            pass

        assert any(m.get("event") == "error" and "Send 'join' first" in m.get("detail", "") for m in ws.sent_messages)


class TestCollabCli:
    def test_collab_create(self):
        from typer.testing import CliRunner
        from vector_studio.cli import app

        runner = CliRunner()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps({
                "room_id": "abc123",
                "owner": "alice",
                "created_at": "2024-01-01T00:00:00",
            }).encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            result = runner.invoke(app, ["collab", "create", "--owner", "alice"])
        assert result.exit_code == 0
        assert "abc123" in result.output
        assert "alice" in result.output

    def test_collab_join(self):
        from typer.testing import CliRunner
        from vector_studio.cli import app

        runner = CliRunner()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps({
                "room_id": "abc123",
                "owner": "alice",
                "client_count": 2,
                "operation_count": 5,
                "next_version": 6,
            }).encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            result = runner.invoke(app, ["collab", "join", "abc123"])
        assert result.exit_code == 0
        assert "abc123" in result.output
        assert "Clients: 2" in result.output

    def test_collab_status(self):
        from typer.testing import CliRunner
        from vector_studio.cli import app

        runner = CliRunner()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps({
                "room_id": "abc123",
                "owner": "alice",
                "created_at": "2024-01-01T00:00:00",
                "client_count": 1,
                "operation_count": 0,
                "next_version": 1,
            }).encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            result = runner.invoke(app, ["collab", "status", "abc123"])
        assert result.exit_code == 0
        assert "alice" in result.output
        assert "Clients" in result.output

    def test_collab_history(self):
        from typer.testing import CliRunner
        from vector_studio.cli import app

        runner = CliRunner()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps({
                "operations": [
                    {"op_id": "op1", "client_id": "c1", "type": "param_change", "version": 1},
                    {"op_id": "op2", "client_id": "c2", "type": "preview_update", "version": 2},
                ],
            }).encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            result = runner.invoke(app, ["collab", "history", "abc123"])
        assert result.exit_code == 0
        assert "op1" in result.output
        assert "op2" in result.output
        assert "param_change" in result.output

    def test_collab_join_not_found(self):
        from typer.testing import CliRunner
        from vector_studio.cli import app
        import urllib.error

        runner = CliRunner()
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(
            url="http://localhost:8000/collab/rooms/bad",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=None,
        )):
            result = runner.invoke(app, ["collab", "join", "bad"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "API error" in result.output

    def test_collab_history_empty(self):
        from typer.testing import CliRunner
        from vector_studio.cli import app

        runner = CliRunner()
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps({"operations": []}).encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            result = runner.invoke(app, ["collab", "history", "abc123"])
        assert result.exit_code == 0
        assert "No operations" in result.output
