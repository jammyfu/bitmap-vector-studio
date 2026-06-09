import json
import time
from pathlib import Path

import pytest

from vector_studio.cache_manager import CacheManager, DiskCache, LRUCache


class TestLRUCache:
    def test_basic_get_set(self):
        """LRU缓存基本读写."""
        cache = LRUCache(maxsize=2)
        cache.set("a", 1)
        assert cache.get("a") == 1

    def test_lru_eviction(self):
        """超出容量时淘汰最久未使用."""
        cache = LRUCache(maxsize=2)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3

    def test_ttl_expiration(self):
        """TTL过期后自动失效."""
        cache = LRUCache(maxsize=10, ttl=0.1)
        cache.set("a", 1)
        assert cache.get("a") == 1
        time.sleep(0.15)
        assert cache.get("a") is None

    def test_clear(self):
        """清空缓存."""
        cache = LRUCache(maxsize=10)
        cache.set("a", 1)
        cache.clear()
        assert cache.get("a") is None
        assert len(cache) == 0

    def test_thread_safety(self):
        """多线程并发读写安全."""
        import threading

        cache = LRUCache(maxsize=100)
        errors = []

        def writer():
            for i in range(100):
                try:
                    cache.set(str(i), i)
                except Exception as e:
                    errors.append(e)

        def reader():
            for i in range(100):
                try:
                    cache.get(str(i))
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=writer) for _ in range(4)]
        threads += [threading.Thread(target=reader) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors


class TestDiskCache:
    def test_basic_get_set(self, tmp_path):
        """磁盘缓存基本读写."""
        cache = DiskCache(tmp_path, max_size_mb=10)
        cache.set("key", b"value")
        assert cache.get("key") == b"value"

    def test_ttl_expiration(self, tmp_path):
        """磁盘缓存TTL过期."""
        cache = DiskCache(tmp_path, max_size_mb=10)
        cache.set("key", b"value", ttl=0.1)
        assert cache.get("key") == b"value"
        time.sleep(0.15)
        assert cache.get("key") is None

    def test_cleanup_by_size(self, tmp_path):
        """超出容量限制时清理旧文件."""
        cache = DiskCache(tmp_path, max_size_mb=1)
        cache.set("a", b"x" * 600 * 1024)  # ~600KB
        cache.set("b", b"y" * 600 * 1024)  # ~600KB
        # 总大小超过1MB，应触发清理
        cache.set("c", b"z" * 100 * 1024)
        # 至少有一个旧文件被删除
        assert sum(1 for _ in tmp_path.glob("*.cache")) <= 3

    def test_clear(self, tmp_path):
        """清空磁盘缓存."""
        cache = DiskCache(tmp_path, max_size_mb=10)
        cache.set("a", b"1")
        cache.set("b", b"2")
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None
        assert len(list(tmp_path.glob("*"))) == 0


class TestCacheManager:
    def test_memory_cache_hit(self, tmp_path):
        """内存缓存命中."""
        mgr = CacheManager(cache_dir=tmp_path)
        mgr.set("k", "v", level="memory")
        assert mgr.get("k", level="memory") == "v"
        assert mgr.get("k", level="all") == "v"

    def test_disk_cache_and_backfill(self, tmp_path):
        """磁盘缓存并回填内存."""
        mgr = CacheManager(cache_dir=tmp_path)
        mgr.set("k", "v", level="disk")
        # 从磁盘读取并回填内存
        assert mgr.get("k", level="all") == b'"v"'
        # 再次读取应从内存命中
        assert mgr.get("k", level="all") == b'"v"'

    def test_clear_levels(self, tmp_path):
        """分级清空缓存."""
        mgr = CacheManager(cache_dir=tmp_path)
        mgr.set("a", 1, level="memory")
        mgr.set("b", 2, level="disk")
        mgr.clear(level="memory")
        assert mgr.get("a", level="all") is None
        # 磁盘缓存仍存在（不触发get避免回填内存）
        mgr.clear(level="disk")
        assert mgr.get("b", level="all") is None
        # 同时清空两级
        mgr.set("c", 3, level="all")
        mgr.clear(level="all")
        assert mgr.get("c", level="all") is None

    def test_conversion_result_roundtrip(self, tmp_path):
        """转换结果缓存读写."""
        mgr = CacheManager(cache_dir=tmp_path)
        result = {"svg_path": "/tmp/out.svg", "engine": "vtracer"}
        mgr.set_conversion_result("/tmp/in.png", "hash123", result, ttl=3600)
        loaded = mgr.get_conversion_result("/tmp/in.png", "hash123")
        assert loaded == result

    def test_preview_roundtrip(self, tmp_path):
        """预览缓存读写."""
        mgr = CacheManager(cache_dir=tmp_path)
        data = b"fake preview bytes"
        mgr.set_preview("/tmp/in.png", "logo", (100, 100), data, ttl=600)
        loaded = mgr.get_preview("/tmp/in.png", "logo", (100, 100))
        assert loaded == data

    def test_stats(self, tmp_path):
        """缓存统计信息."""
        mgr = CacheManager(cache_dir=tmp_path)
        mgr.set("a", 1, level="all")
        stats = mgr.stats()
        assert stats["memory_entries"] == 1
        assert stats["disk_entries"] >= 1
        assert "disk_size_mb" in stats
        assert stats["disk_max_size_mb"] == 200

    def test_get_nonexistent(self, tmp_path):
        """获取不存在的键返回None."""
        mgr = CacheManager(cache_dir=tmp_path)
        assert mgr.get("nonexistent", level="all") is None
        assert mgr.get_conversion_result("/tmp/x.png", "nohash") is None
        assert mgr.get_preview("/tmp/x.png", "p", (1, 1)) is None
