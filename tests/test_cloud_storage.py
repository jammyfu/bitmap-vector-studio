from __future__ import annotations

from pathlib import Path

import pytest

from vector_studio.cloud_storage import (
    COSStorage,
    LocalStorage,
    OSSStorage,
    S3Storage,
    StorageConfig,
    StorageManager,
)


class TestLocalStorage:
    def test_upload_creates_file(self, tmp_path: Path):
        """Upload must copy the file to the local storage base dir."""
        storage = LocalStorage(tmp_path / "local")
        source = tmp_path / "source.txt"
        source.write_text("hello")
        url = storage.upload(source, "subdir/target.txt")
        target = tmp_path / "local" / "subdir" / "target.txt"
        assert target.exists()
        assert target.read_text() == "hello"
        assert url == str(target)

    def test_download_creates_file(self, tmp_path: Path):
        """Download must copy the file from the local storage base dir."""
        storage = LocalStorage(tmp_path / "local")
        source = tmp_path / "local" / "remote.txt"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("remote content")
        dest = tmp_path / "downloaded.txt"
        storage.download("remote.txt", dest)
        assert dest.exists()
        assert dest.read_text() == "remote content"

    def test_delete_removes_file(self, tmp_path: Path):
        """Delete must remove the file and return True if it existed."""
        storage = LocalStorage(tmp_path / "local")
        target = tmp_path / "local" / "delete_me.txt"
        target.write_text("bye")
        assert storage.delete("delete_me.txt") is True
        assert not target.exists()
        assert storage.delete("delete_me.txt") is False

    def test_list_files_returns_entries(self, tmp_path: Path):
        """list_files must return all files under the prefix."""
        import os
        storage = LocalStorage(tmp_path / "local")
        (tmp_path / "local" / "a" / "b").mkdir(parents=True)
        (tmp_path / "local" / "a" / "file1.txt").write_text("1")
        (tmp_path / "local" / "a" / "b" / "file2.txt").write_text("2")
        results = storage.list_files("a")
        keys = {r["key"] for r in results}
        assert f"a{os.sep}file1.txt" in keys
        assert f"a{os.sep}b{os.sep}file2.txt" in keys

    def test_exists_checks_file_presence(self, tmp_path: Path):
        """exists must return True only for existing files."""
        storage = LocalStorage(tmp_path / "local")
        (tmp_path / "local" / "present.txt").write_text("yes")
        assert storage.exists("present.txt") is True
        assert storage.exists("missing.txt") is False


class TestStorageManager:
    def test_add_and_get_storage(self, tmp_path: Path):
        """add_storage must create a storage and get_storage must retrieve it."""
        config_file = tmp_path / "storage.json"
        manager = StorageManager(config_file=config_file)
        config = StorageConfig(provider="local", bucket=str(tmp_path / "bucket"))
        storage = manager.add_storage("my-local", config)
        assert isinstance(storage, LocalStorage)
        assert manager.get_storage("my-local") is storage
        assert "my-local" in manager.list_storages()

    def test_get_missing_storage_raises(self, tmp_path: Path):
        """get_storage must raise KeyError for unknown storage names."""
        manager = StorageManager(config_file=tmp_path / "storage.json")
        with pytest.raises(KeyError, match="存储不存在"):
            manager.get_storage("missing")

    def test_sync_to_cloud(self, tmp_path: Path):
        """sync_to_cloud must upload all files from a local directory."""
        manager = StorageManager(config_file=tmp_path / "storage.json")
        bucket = tmp_path / "bucket"
        bucket.mkdir()
        manager.add_storage("local-bucket", StorageConfig(provider="local", bucket=str(bucket)))
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.txt").write_text("A")
        (src / "sub").mkdir()
        (src / "sub" / "b.txt").write_text("B")
        urls = manager.sync_to_cloud(src, "local-bucket", remote_prefix="backup")
        assert len(urls) == 2
        assert (bucket / "backup" / "a.txt").exists()
        assert (bucket / "backup" / "sub" / "b.txt").exists()

    def test_sync_from_cloud(self, tmp_path: Path):
        """sync_from_cloud must download all files matching the prefix."""
        manager = StorageManager(config_file=tmp_path / "storage.json")
        bucket = tmp_path / "bucket"
        bucket.mkdir()
        manager.add_storage("local-bucket", StorageConfig(provider="local", bucket=str(bucket)))
        (bucket / "backup").mkdir()
        (bucket / "backup" / "a.txt").write_text("A")
        (bucket / "backup" / "sub").mkdir()
        (bucket / "backup" / "sub" / "b.txt").write_text("B")
        dest = tmp_path / "dest"
        dest.mkdir()
        paths = manager.sync_from_cloud("local-bucket", "backup", dest)
        assert len(paths) == 2
        assert (dest / "a.txt").exists()
        assert (dest / "sub" / "b.txt").exists()

    def test_persistence(self, tmp_path: Path):
        """Storage configurations must persist to disk and reload."""
        config_file = tmp_path / "storage.json"
        manager = StorageManager(config_file=config_file)
        manager.add_storage("persist", StorageConfig(provider="local", bucket=str(tmp_path / "b")))
        # Create a new manager pointing to the same file
        manager2 = StorageManager(config_file=config_file)
        assert "persist" in manager2.list_storages()


class TestCloudStorageFallbacks:
    def test_s3_fallback_without_boto3(self, tmp_path: Path):
        """S3Storage must fall back to local storage when boto3 is missing."""
        config = StorageConfig(provider="s3", bucket="my-bucket", region="us-east-1")
        storage = S3Storage(config)
        source = tmp_path / "file.txt"
        source.write_text("s3-fallback")
        url = storage.upload(source, "key.txt")
        assert "key.txt" in url
        # Verify fallback file exists
        assert storage._local_fallback.exists("key.txt")

    def test_oss_fallback_without_oss2(self, tmp_path: Path):
        """OSSStorage must fall back to local storage when oss2 is missing."""
        config = StorageConfig(
            provider="oss", bucket="my-bucket", endpoint="oss-cn-hangzhou.aliyuncs.com"
        )
        storage = OSSStorage(config)
        source = tmp_path / "file.txt"
        source.write_text("oss-fallback")
        url = storage.upload(source, "key.txt")
        assert "key.txt" in url
        assert storage._local_fallback.exists("key.txt")

    def test_cos_fallback_without_qcloud_cos(self, tmp_path: Path):
        """COSStorage must fall back to local storage when qcloud_cos is missing."""
        config = StorageConfig(
            provider="cos", bucket="my-bucket", region="ap-guangzhou"
        )
        storage = COSStorage(config)
        source = tmp_path / "file.txt"
        source.write_text("cos-fallback")
        url = storage.upload(source, "key.txt")
        assert "key.txt" in url
        assert storage._local_fallback.exists("key.txt")

    def test_unsupported_provider_raises(self, tmp_path: Path):
        """StorageManager must raise ValueError for unsupported providers."""
        manager = StorageManager(config_file=tmp_path / "storage.json")
        config = StorageConfig(provider="azure", bucket="bucket")
        with pytest.raises(ValueError, match="不支持的存储提供商"):
            manager.add_storage("bad", config)
