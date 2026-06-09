"""Bitmap Vector Studio 云存储集成.

支持 S3、阿里云 OSS、腾讯云 COS、本地文件系统.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class StorageConfig:
    """存储配置."""

    provider: str  # 's3', 'oss', 'cos', 'local'
    bucket: str
    region: str | None = None
    endpoint: str | None = None
    access_key: str | None = None
    secret_key: str | None = None
    prefix: str = ""


class CloudStorage(ABC):
    """云存储抽象基类."""

    @abstractmethod
    def upload(self, local_path: Path, remote_key: str) -> str:
        """上传文件，返回URL."""
        pass

    @abstractmethod
    def download(self, remote_key: str, local_path: Path) -> None:
        """下载文件."""
        pass

    @abstractmethod
    def delete(self, remote_key: str) -> bool:
        """删除文件."""
        pass

    @abstractmethod
    def list_files(self, prefix: str = "") -> list[dict]:
        """列出文件."""
        pass

    @abstractmethod
    def exists(self, remote_key: str) -> bool:
        """检查文件是否存在."""
        pass


class LocalStorage(CloudStorage):
    """本地文件系统存储（用于测试和本地模式）."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def upload(self, local_path: Path, remote_key: str) -> str:
        target = self.base_dir / remote_key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(local_path.read_bytes())
        return str(target)

    def download(self, remote_key: str, local_path: Path) -> None:
        source = self.base_dir / remote_key
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(source.read_bytes())

    def delete(self, remote_key: str) -> bool:
        target = self.base_dir / remote_key
        if target.exists():
            target.unlink()
            return True
        return False

    def list_files(self, prefix: str = "") -> list[dict]:
        results = []
        search_dir = self.base_dir / prefix
        if search_dir.exists():
            for f in search_dir.rglob("*"):
                if f.is_file():
                    rel = f.relative_to(self.base_dir)
                    results.append({
                        "key": str(rel),
                        "size": f.stat().st_size,
                        "modified": f.stat().st_mtime,
                    })
        return results

    def exists(self, remote_key: str) -> bool:
        return (self.base_dir / remote_key).exists()


class S3Storage(CloudStorage):
    """AWS S3 存储（使用标准库模拟）."""

    def __init__(self, config: StorageConfig):
        self.config = config
        self._local_fallback = LocalStorage(
            Path.home() / ".bitmap_vector_studio" / "cloud" / "s3"
        )

    def upload(self, local_path: Path, remote_key: str) -> str:
        # 如果没有boto3，使用本地回退
        try:
            import boto3

            s3 = boto3.client("s3", region_name=self.config.region)
            full_key = f"{self.config.prefix}/{remote_key}".lstrip("/")
            s3.upload_file(str(local_path), self.config.bucket, full_key)
            return f"s3://{self.config.bucket}/{full_key}"
        except ImportError:
            return self._local_fallback.upload(local_path, remote_key)

    def download(self, remote_key: str, local_path: Path) -> None:
        try:
            import boto3

            s3 = boto3.client("s3", region_name=self.config.region)
            full_key = f"{self.config.prefix}/{remote_key}".lstrip("/")
            s3.download_file(self.config.bucket, full_key, str(local_path))
        except ImportError:
            self._local_fallback.download(remote_key, local_path)

    def delete(self, remote_key: str) -> bool:
        try:
            import boto3

            s3 = boto3.client("s3", region_name=self.config.region)
            full_key = f"{self.config.prefix}/{remote_key}".lstrip("/")
            s3.delete_object(Bucket=self.config.bucket, Key=full_key)
            return True
        except ImportError:
            return self._local_fallback.delete(remote_key)

    def list_files(self, prefix: str = "") -> list[dict]:
        try:
            import boto3

            s3 = boto3.client("s3", region_name=self.config.region)
            full_prefix = f"{self.config.prefix}/{prefix}".lstrip("/")
            response = s3.list_objects_v2(Bucket=self.config.bucket, Prefix=full_prefix)
            return [
                {
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "modified": obj["LastModified"].isoformat(),
                }
                for obj in response.get("Contents", [])
            ]
        except ImportError:
            return self._local_fallback.list_files(prefix)

    def exists(self, remote_key: str) -> bool:
        try:
            import boto3

            s3 = boto3.client("s3", region_name=self.config.region)
            full_key = f"{self.config.prefix}/{remote_key}".lstrip("/")
            s3.head_object(Bucket=self.config.bucket, Key=full_key)
            return True
        except ImportError:
            return self._local_fallback.exists(remote_key)
        except Exception:
            return False


class OSSStorage(CloudStorage):
    """阿里云 OSS 存储."""

    def __init__(self, config: StorageConfig):
        self.config = config
        self._local_fallback = LocalStorage(
            Path.home() / ".bitmap_vector_studio" / "cloud" / "oss"
        )

    def upload(self, local_path: Path, remote_key: str) -> str:
        try:
            import oss2

            auth = oss2.Auth(self.config.access_key, self.config.secret_key)
            bucket = oss2.Bucket(auth, self.config.endpoint, self.config.bucket)
            full_key = f"{self.config.prefix}/{remote_key}".lstrip("/")
            bucket.put_object_from_file(full_key, str(local_path))
            return f"oss://{self.config.bucket}/{full_key}"
        except ImportError:
            return self._local_fallback.upload(local_path, remote_key)

    def download(self, remote_key: str, local_path: Path) -> None:
        try:
            import oss2

            auth = oss2.Auth(self.config.access_key, self.config.secret_key)
            bucket = oss2.Bucket(auth, self.config.endpoint, self.config.bucket)
            full_key = f"{self.config.prefix}/{remote_key}".lstrip("/")
            bucket.get_object_to_file(full_key, str(local_path))
        except ImportError:
            self._local_fallback.download(remote_key, local_path)

    def delete(self, remote_key: str) -> bool:
        try:
            import oss2

            auth = oss2.Auth(self.config.access_key, self.config.secret_key)
            bucket = oss2.Bucket(auth, self.config.endpoint, self.config.bucket)
            full_key = f"{self.config.prefix}/{remote_key}".lstrip("/")
            bucket.delete_object(full_key)
            return True
        except ImportError:
            return self._local_fallback.delete(remote_key)

    def list_files(self, prefix: str = "") -> list[dict]:
        try:
            import oss2

            auth = oss2.Auth(self.config.access_key, self.config.secret_key)
            bucket = oss2.Bucket(auth, self.config.endpoint, self.config.bucket)
            full_prefix = f"{self.config.prefix}/{prefix}".lstrip("/")
            objects = bucket.list_objects(prefix=full_prefix)
            return [
                {"key": obj.key, "size": obj.size, "modified": obj.last_modified}
                for obj in objects.object_list
            ]
        except ImportError:
            return self._local_fallback.list_files(prefix)

    def exists(self, remote_key: str) -> bool:
        try:
            import oss2

            auth = oss2.Auth(self.config.access_key, self.config.secret_key)
            bucket = oss2.Bucket(auth, self.config.endpoint, self.config.bucket)
            full_key = f"{self.config.prefix}/{remote_key}".lstrip("/")
            return bucket.object_exists(full_key)
        except ImportError:
            return self._local_fallback.exists(remote_key)


class COSStorage(CloudStorage):
    """腾讯云 COS 存储."""

    def __init__(self, config: StorageConfig):
        self.config = config
        self._local_fallback = LocalStorage(
            Path.home() / ".bitmap_vector_studio" / "cloud" / "cos"
        )

    def upload(self, local_path: Path, remote_key: str) -> str:
        try:
            from qcloud_cos import CosConfig, CosS3Client

            cos_config = CosConfig(
                Region=self.config.region,
                SecretId=self.config.access_key,
                SecretKey=self.config.secret_key,
            )
            client = CosS3Client(cos_config)
            full_key = f"{self.config.prefix}/{remote_key}".lstrip("/")
            client.upload_file(
                Bucket=self.config.bucket,
                LocalFilePath=str(local_path),
                Key=full_key,
            )
            return f"cos://{self.config.bucket}/{full_key}"
        except ImportError:
            return self._local_fallback.upload(local_path, remote_key)

    def download(self, remote_key: str, local_path: Path) -> None:
        try:
            from qcloud_cos import CosConfig, CosS3Client

            cos_config = CosConfig(
                Region=self.config.region,
                SecretId=self.config.access_key,
                SecretKey=self.config.secret_key,
            )
            client = CosS3Client(cos_config)
            full_key = f"{self.config.prefix}/{remote_key}".lstrip("/")
            client.download_file(
                Bucket=self.config.bucket,
                Key=full_key,
                DestFilePath=str(local_path),
            )
        except ImportError:
            self._local_fallback.download(remote_key, local_path)

    def delete(self, remote_key: str) -> bool:
        try:
            from qcloud_cos import CosConfig, CosS3Client

            cos_config = CosConfig(
                Region=self.config.region,
                SecretId=self.config.access_key,
                SecretKey=self.config.secret_key,
            )
            client = CosS3Client(cos_config)
            full_key = f"{self.config.prefix}/{remote_key}".lstrip("/")
            client.delete_object(Bucket=self.config.bucket, Key=full_key)
            return True
        except ImportError:
            return self._local_fallback.delete(remote_key)

    def list_files(self, prefix: str = "") -> list[dict]:
        try:
            from qcloud_cos import CosConfig, CosS3Client

            cos_config = CosConfig(
                Region=self.config.region,
                SecretId=self.config.access_key,
                SecretKey=self.config.secret_key,
            )
            client = CosS3Client(cos_config)
            full_prefix = f"{self.config.prefix}/{prefix}".lstrip("/")
            response = client.list_objects(
                Bucket=self.config.bucket, Prefix=full_prefix
            )
            contents = response.get("Contents", [])
            return [
                {
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "modified": obj["LastModified"],
                }
                for obj in contents
            ]
        except ImportError:
            return self._local_fallback.list_files(prefix)

    def exists(self, remote_key: str) -> bool:
        try:
            from qcloud_cos import CosConfig, CosS3Client

            cos_config = CosConfig(
                Region=self.config.region,
                SecretId=self.config.access_key,
                SecretKey=self.config.secret_key,
            )
            client = CosS3Client(cos_config)
            full_key = f"{self.config.prefix}/{remote_key}".lstrip("/")
            response = client.object_exists(
                Bucket=self.config.bucket, Key=full_key
            )
            return response
        except ImportError:
            return self._local_fallback.exists(remote_key)


class StorageManager:
    """存储管理器."""

    def __init__(self, config_file: Path | None = None):
        self.config_file = config_file or Path.home() / ".bitmap_vector_studio" / "storage.json"
        self._storages: dict[str, CloudStorage] = {}
        self._load_configs()

    def _load_configs(self) -> None:
        if self.config_file.exists():
            try:
                data = json.loads(self.config_file.read_text(encoding="utf-8"))
                for name, cfg in data.items():
                    self.add_storage(name, StorageConfig(**cfg))
            except Exception:
                pass

    def _save_configs(self) -> None:
        configs = {}
        for name, storage in self._storages.items():
            if isinstance(storage, LocalStorage):
                configs[name] = {
                    "provider": "local",
                    "bucket": str(storage.base_dir),
                }
            elif isinstance(storage, (S3Storage, OSSStorage, COSStorage)):
                # 不保存敏感信息
                configs[name] = {
                    "provider": storage.config.provider,
                    "bucket": storage.config.bucket,
                }
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config_file.write_text(
            json.dumps(configs, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def add_storage(self, name: str, config: StorageConfig) -> CloudStorage:
        """添加存储."""
        if config.provider == "local":
            storage = LocalStorage(Path(config.bucket))
        elif config.provider == "s3":
            storage = S3Storage(config)
        elif config.provider == "oss":
            storage = OSSStorage(config)
        elif config.provider == "cos":
            storage = COSStorage(config)
        else:
            raise ValueError(f"不支持的存储提供商: {config.provider}")

        self._storages[name] = storage
        self._save_configs()
        return storage

    def get_storage(self, name: str) -> CloudStorage:
        """获取存储."""
        if name not in self._storages:
            raise KeyError(f"存储不存在: {name}")
        return self._storages[name]

    def list_storages(self) -> list[str]:
        """列出所有存储."""
        return list(self._storages.keys())

    def sync_to_cloud(
        self, local_dir: Path, storage_name: str, remote_prefix: str = ""
    ) -> list[str]:
        """同步本地目录到云端."""
        storage = self.get_storage(storage_name)
        uploaded = []

        for file in local_dir.rglob("*"):
            if file.is_file():
                rel = file.relative_to(local_dir)
                remote_key = f"{remote_prefix}/{rel}".lstrip("/")
                url = storage.upload(file, remote_key)
                uploaded.append(url)

        return uploaded

    def sync_from_cloud(
        self, storage_name: str, remote_prefix: str, local_dir: Path
    ) -> list[Path]:
        """同步云端到本地."""
        storage = self.get_storage(storage_name)
        downloaded = []

        for obj in storage.list_files(remote_prefix):
            remote_key = obj["key"]
            # Normalize path separators for cross-platform compatibility
            prefix_path = Path(remote_prefix)
            key_path = Path(remote_key)
            try:
                rel = str(key_path.relative_to(prefix_path))
            except ValueError:
                rel = remote_key[len(remote_prefix):].lstrip("/\\")
            local_path = local_dir / rel
            local_path.parent.mkdir(parents=True, exist_ok=True)
            storage.download(remote_key, local_path)
            downloaded.append(local_path)

        return downloaded
