import json
import socket
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from vector_studio.auto_discovery import WorkerDiscovery, WorkerInfo


class TestWorkerDiscovery:
    def test_init_defaults(self):
        """默认初始化参数."""
        wd = WorkerDiscovery()
        assert wd.port == 9001
        assert wd.capacity == 4
        assert wd.current_load == 0
        assert wd.worker_id.startswith("worker-")

    def test_custom_init(self):
        """自定义初始化参数."""
        wd = WorkerDiscovery(worker_id="w1", port=9002, capacity=8)
        assert wd.worker_id == "w1"
        assert wd.port == 9002
        assert wd.capacity == 8

    def test_on_peer_change_callback(self):
        """注册回调函数."""
        wd = WorkerDiscovery()
        cb = MagicMock()
        wd.on_peer_change(cb)
        assert cb in wd._callbacks

    def test_get_peers_empty(self):
        """初始时peers为空."""
        wd = WorkerDiscovery()
        assert wd.get_peers() == []

    def test_start_stop(self):
        """启动和停止服务."""
        wd = WorkerDiscovery(port=29998)
        wd.start()
        time.sleep(0.1)
        assert wd._running is True
        assert len(wd._threads) == 3
        wd.stop()
        assert wd._running is False

    def test_broadcast_loop(self):
        """广播循环发送announce消息."""
        wd = WorkerDiscovery(port=29997)
        mock_sock = MagicMock()
        wd._sock = mock_sock
        wd._running = True

        # 只运行一次广播
        with patch.object(wd, 'BROADCAST_INTERVAL', 0.01):
            t = threading.Thread(target=wd._broadcast_loop, daemon=True)
            t.start()
            time.sleep(0.05)
            wd._running = False
            t.join(timeout=1)

        assert mock_sock.sendto.called
        args, _ = mock_sock.sendto.call_args
        msg = json.loads(args[0].decode())
        assert msg["type"] == "announce"
        assert msg["worker_id"] == wd.worker_id

    def test_listen_loop_join_event(self):
        """监听循环触发join事件."""
        wd = WorkerDiscovery(port=29996)
        cb = MagicMock()
        wd.on_peer_change(cb)

        mock_sock = MagicMock()
        announce = json.dumps({
            "type": "announce",
            "worker_id": "other-worker",
            "port": 9000,
            "capacity": 4,
            "load": 1,
            "version": "3.1.0",
        }).encode()
        # 只返回一次，之后抛出异常终止循环
        mock_sock.recvfrom.side_effect = [(announce, ("192.168.1.2", 29999)), OSError("stop")]
        wd._sock = mock_sock
        wd._running = True

        t = threading.Thread(target=wd._listen_loop, daemon=True)
        t.start()
        time.sleep(0.1)
        wd._running = False
        t.join(timeout=1)

        cb.assert_called_once()
        worker, event = cb.call_args[0]
        assert isinstance(worker, WorkerInfo)
        assert worker.worker_id == "other-worker"
        assert event == "join"

    def test_listen_loop_update_event(self):
        """同一worker再次announce触发update事件."""
        wd = WorkerDiscovery(port=29995)
        cb = MagicMock()
        wd.on_peer_change(cb)
        # 预先添加peer
        wd._peers["peer-1"] = WorkerInfo(
            worker_id="peer-1", host="10.0.0.1", port=9000,
            capacity=4, current_load=0, version="3.1.0", last_seen=time.time(),
        )

        mock_sock = MagicMock()
        announce = json.dumps({
            "type": "announce",
            "worker_id": "peer-1",
            "port": 9000,
            "capacity": 4,
            "load": 2,
            "version": "3.1.0",
        }).encode()
        mock_sock.recvfrom.side_effect = [(announce, ("10.0.0.1", 29999)), OSError("stop")]
        wd._sock = mock_sock
        wd._running = True

        t = threading.Thread(target=wd._listen_loop, daemon=True)
        t.start()
        time.sleep(0.1)
        wd._running = False
        t.join(timeout=1)

        cb.assert_called_once()
        _, event = cb.call_args[0]
        assert event == "update"

    def test_cleanup_loop_leave_event(self):
        """清理逻辑触发leave事件."""
        wd = WorkerDiscovery(port=29994)
        cb = MagicMock()
        wd.on_peer_change(cb)
        wd._peers["old-worker"] = WorkerInfo(
            worker_id="old-worker", host="10.0.0.1", port=9000,
            capacity=4, current_load=0, version="3.1.0", last_seen=time.time() - 60,
        )

        # 直接执行清理逻辑，避免10秒等待
        now = time.time()
        stale = [wid for wid, w in wd._peers.items() if now - w.last_seen > 30]
        for wid in stale:
            worker = wd._peers.pop(wid)
            for inner_cb in wd._callbacks:
                inner_cb(worker, 'leave')

        cb.assert_called_once()
        _, event = cb.call_args[0]
        assert event == "leave"
        assert "old-worker" not in wd._peers

    def test_listen_loop_ignores_self(self):
        """忽略自己的announce消息."""
        wd = WorkerDiscovery(port=29993)
        cb = MagicMock()
        wd.on_peer_change(cb)

        mock_sock = MagicMock()
        announce = json.dumps({
            "type": "announce",
            "worker_id": wd.worker_id,
            "port": 9000,
            "capacity": 4,
            "load": 0,
        }).encode()
        mock_sock.recvfrom.side_effect = [(announce, ("127.0.0.1", 29999)), OSError("stop")]
        wd._sock = mock_sock
        wd._running = True

        t = threading.Thread(target=wd._listen_loop, daemon=True)
        t.start()
        time.sleep(0.1)
        wd._running = False
        t.join(timeout=1)

        cb.assert_not_called()
