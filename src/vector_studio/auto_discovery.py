"""渲染农场Worker自动发现服务.

通过mDNS/UDP广播自动发现局域网内的Worker节点.
"""

import json
import socket
import threading
import time
from dataclasses import dataclass
from typing import Callable


@dataclass
class WorkerInfo:
    worker_id: str
    host: str
    port: int
    capacity: int
    current_load: int
    version: str
    last_seen: float


class WorkerDiscovery:
    """Worker节点自动发现."""

    DISCOVERY_PORT = 29999
    BROADCAST_INTERVAL = 5

    def __init__(self, worker_id: str | None = None, port: int = 9001, capacity: int = 4):
        self.worker_id = worker_id or f"worker-{socket.gethostname()}"
        self.port = port
        self.capacity = capacity
        self.current_load = 0
        self._peers: dict[str, WorkerInfo] = {}
        self._callbacks: list[Callable[[WorkerInfo, str], None]] = []
        self._running = False
        self._sock: socket.socket | None = None
        self._threads: list[threading.Thread] = []

    def on_peer_change(self, callback: Callable[[WorkerInfo, str], None]) -> None:
        """注册节点变化回调. event: 'join' | 'leave' | 'update'"""
        self._callbacks.append(callback)

    def start(self) -> None:
        self._running = True
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(('', self.DISCOVERY_PORT))

        # 广播线程
        t1 = threading.Thread(target=self._broadcast_loop, daemon=True)
        t1.start()
        self._threads.append(t1)

        # 监听线程
        t2 = threading.Thread(target=self._listen_loop, daemon=True)
        t2.start()
        self._threads.append(t2)

        # 清理线程
        t3 = threading.Thread(target=self._cleanup_loop, daemon=True)
        t3.start()
        self._threads.append(t3)

    def stop(self) -> None:
        self._running = False
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass

    def get_peers(self) -> list[WorkerInfo]:
        return list(self._peers.values())

    def _broadcast_loop(self) -> None:
        while self._running:
            try:
                msg = json.dumps({
                    'type': 'announce',
                    'worker_id': self.worker_id,
                    'port': self.port,
                    'capacity': self.capacity,
                    'load': self.current_load,
                    'version': '3.1.0',
                })
                if self._sock:
                    self._sock.sendto(msg.encode(), ('<broadcast>', self.DISCOVERY_PORT))
            except Exception:
                pass
            time.sleep(self.BROADCAST_INTERVAL)

    def _listen_loop(self) -> None:
        while self._running:
            try:
                if self._sock is None:
                    break
                data, addr = self._sock.recvfrom(1024)
                msg = json.loads(data.decode())
                if msg.get('type') == 'announce' and msg.get('worker_id') != self.worker_id:
                    worker = WorkerInfo(
                        worker_id=msg['worker_id'],
                        host=addr[0],
                        port=msg['port'],
                        capacity=msg['capacity'],
                        current_load=msg['load'],
                        version=msg.get('version', 'unknown'),
                        last_seen=time.time(),
                    )
                    event = 'join' if worker.worker_id not in self._peers else 'update'
                    self._peers[worker.worker_id] = worker
                    for cb in self._callbacks:
                        cb(worker, event)
            except Exception:
                pass

    def _cleanup_loop(self) -> None:
        while self._running:
            time.sleep(10)
            now = time.time()
            stale = [wid for wid, w in self._peers.items() if now - w.last_seen > 30]
            for wid in stale:
                worker = self._peers.pop(wid)
                for cb in self._callbacks:
                    cb(worker, 'leave')
