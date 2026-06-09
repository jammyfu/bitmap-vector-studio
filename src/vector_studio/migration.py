"""数据迁移工具.

支持配置和数据的版本升级迁移.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class MigrationManager:
    """迁移管理器."""

    CURRENT_VERSION = 3

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or Path.home() / '.bitmap_vector_studio'
        self.version_file = self.data_dir / 'version.json'

    def get_current_version(self) -> int:
        if self.version_file.exists():
            try:
                data = json.loads(self.version_file.read_text())
                return data.get('schema_version', 0)
            except Exception:
                return 0
        return 0

    def needs_migration(self) -> bool:
        return self.get_current_version() < self.CURRENT_VERSION

    def migrate(self) -> list[str]:
        """执行迁移，返回迁移日志."""
        current = self.get_current_version()
        logs = []

        for version in range(current + 1, self.CURRENT_VERSION + 1):
            method = getattr(self, f'_migrate_v{version}', None)
            if method:
                logs.append(f"Migrating to v{version}...")
                try:
                    method()
                    logs.append(f"  ✓ v{version} complete")
                except Exception as e:
                    logs.append(f"  ✗ v{version} failed: {e}")
            else:
                logs.append(f"  - v{version} no migration needed")

        # 更新版本号
        self.version_file.write_text(json.dumps({'schema_version': self.CURRENT_VERSION}))
        logs.append(f"Schema version updated to {self.CURRENT_VERSION}")
        return logs

    def _migrate_v1(self) -> None:
        """v0 → v1: 创建基本目录结构."""
        (self.data_dir / 'presets').mkdir(exist_ok=True)
        (self.data_dir / 'history').mkdir(exist_ok=True)

    def _migrate_v2(self) -> None:
        """v1 → v2: 历史记录格式升级."""
        old_history = self.data_dir / 'history.json'
        if old_history.exists():
            new_history = self.data_dir / 'history.jsonl'
            data = json.loads(old_history.read_text())
            with open(new_history, 'w') as f:
                for item in data:
                    f.write(json.dumps(item) + '\n')
            old_history.rename(old_history.with_suffix('.json.bak'))

    def _migrate_v3(self) -> None:
        """v2 → v3: 添加缓存和报告目录."""
        (self.data_dir / 'cache').mkdir(exist_ok=True)
        (self.data_dir / 'reports').mkdir(exist_ok=True)
        (self.data_dir / 'plugin_market').mkdir(exist_ok=True)
