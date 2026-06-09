"""Bitmap Vector Studio 缓存管理器.

提供多级缓存:
- L1: 内存缓存 (LRU, TTL)
- L2: 磁盘缓存 (文件系统)
- L3: 持久化缓存 (SQLite)
"""

import hashlib
import json
import sqlite3
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any


class LRUCache:
    """线程安全的LRU内存缓存."""

    def __init__(self, maxsize: int = 128, ttl: int | None = None):
        self.maxsize = maxsize
        self.ttl = ttl
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            if key not in self._cache:
                return None
            value, timestamp = self._cache[key]
            if self.ttl and time.time() - timestamp > self.ttl:
                del self._cache[key]
                return None
            self._cache.move_to_end(key)
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._cache[key] = (value, time.time())
            self._cache.move_to_end(key)
            if len(self._cache) > self.maxsize:
                self._cache.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)


class DiskCache:
    """磁盘文件缓存."""

    def __init__(self, cache_dir: Path, max_size_mb: int = 100):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_mb = max_size_mb

    def _key_to_path(self, key: str) -> Path:
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{hash_key}.cache"

    def get(self, key: str) -> bytes | None:
        path = self._key_to_path(key)
        if not path.exists():
            return None
        # 检查是否过期
        meta_path = path.with_suffix('.meta')
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
                if meta.get('expires') and time.time() > meta['expires']:
                    path.unlink(missing_ok=True)
                    meta_path.unlink(missing_ok=True)
                    return None
            except (json.JSONDecodeError, OSError):
                pass
        try:
            return path.read_bytes()
        except OSError:
            return None

    def set(self, key: str, data: bytes, ttl: int | None = None) -> None:
        path = self._key_to_path(key)
        try:
            path.write_bytes(data)
            meta = {'created': time.time()}
            if ttl:
                meta['expires'] = time.time() + ttl
            path.with_suffix('.meta').write_text(json.dumps(meta))
            self._cleanup_if_needed()
        except OSError:
            pass

    def _cleanup_if_needed(self) -> None:
        # 如果总大小超过限制，删除最旧的文件
        files = sorted(self.cache_dir.glob('*.cache'), key=lambda p: p.stat().st_mtime)
        total_mb = sum(f.stat().st_size for f in files) / (1024 * 1024)
        while total_mb > self.max_size_mb and files:
            oldest = files.pop(0)
            oldest.unlink(missing_ok=True)
            oldest.with_suffix('.meta').unlink(missing_ok=True)
            total_mb = sum(f.stat().st_size for f in files) / (1024 * 1024)

    def clear(self) -> None:
        for f in self.cache_dir.glob('*'):
            f.unlink(missing_ok=True)


class CacheManager:
    """统一缓存管理器."""

    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = cache_dir or Path.home() / '.bitmap_vector_studio' / 'cache'
        self.memory = LRUCache(maxsize=64, ttl=300)  # 5分钟TTL
        self.disk = DiskCache(self.cache_dir / 'disk', max_size_mb=200)
        self._lock = threading.Lock()

    def get(self, key: str, level: str = 'memory') -> Any | None:
        if level in ('memory', 'all'):
            result = self.memory.get(key)
            if result is not None:
                return result
        if level in ('disk', 'all'):
            result = self.disk.get(key)
            if result is not None:
                # 回填内存
                self.memory.set(key, result)
                return result
        return None

    def set(self, key: str, value: Any, level: str = 'memory', ttl: int | None = None) -> None:
        if level in ('memory', 'all'):
            self.memory.set(key, value)
        if level in ('disk', 'all'):
            data = json.dumps(value).encode() if not isinstance(value, bytes) else value
            self.disk.set(key, data, ttl)

    def clear(self, level: str = 'all') -> None:
        if level in ('memory', 'all'):
            self.memory.clear()
        if level in ('disk', 'all'):
            self.disk.clear()

    def get_conversion_result(self, input_path: str, options_hash: str) -> dict | None:
        """获取转换结果缓存."""
        key = f"conv:{hashlib.sha256(f'{input_path}:{options_hash}'.encode()).hexdigest()[:16]}"
        result = self.get(key, 'all')
        if result:
            if isinstance(result, bytes):
                try:
                    return json.loads(result)
                except json.JSONDecodeError:
                    return None
            return result
        return None

    def set_conversion_result(self, input_path: str, options_hash: str, result: dict, ttl: int = 3600) -> None:
        """缓存转换结果."""
        key = f"conv:{hashlib.sha256(f'{input_path}:{options_hash}'.encode()).hexdigest()[:16]}"
        self.set(key, result, 'all', ttl)

    def get_preview(self, input_path: str, preset: str, size: tuple[int, int]) -> bytes | None:
        """获取预览缓存."""
        key = f"preview:{hashlib.sha256(f'{input_path}:{preset}:{size}'.encode()).hexdigest()[:16]}"
        return self.get(key, 'all')

    def set_preview(self, input_path: str, preset: str, size: tuple[int, int], data: bytes, ttl: int = 600) -> None:
        """缓存预览."""
        key = f"preview:{hashlib.sha256(f'{input_path}:{preset}:{size}'.encode()).hexdigest()[:16]}"
        self.set(key, data, 'all', ttl)

    def stats(self) -> dict[str, Any]:
        """返回缓存统计信息."""
        disk_files = list(self.disk.cache_dir.glob('*.cache'))
        disk_size_mb = sum(f.stat().st_size for f in disk_files) / (1024 * 1024)
        return {
            'memory_entries': len(self.memory),
            'disk_entries': len(disk_files),
            'disk_size_mb': round(disk_size_mb, 2),
            'disk_max_size_mb': self.disk.max_size_mb,
            'cache_dir': str(self.cache_dir),
        }
