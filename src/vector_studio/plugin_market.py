"""Bitmap Vector Studio 插件市场.

支持插件的发现、评分、分类、安装、更新.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class PluginPackage:
    """插件包信息."""

    package_id: str
    name: str
    version: str
    description: str
    author: str
    category: str  # 'filter', 'export', 'ai', 'utility'
    tags: list[str]
    rating: float  # 1-5
    downloads: int
    dependencies: list[str]
    min_app_version: str
    source_url: str | None
    install_path: Path | None
    installed: bool
    enabled: bool

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        d = asdict(self)
        if d["install_path"] is not None:
            d["install_path"] = str(d["install_path"])
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PluginPackage:
        """Deserialize from a dict."""
        if data.get("install_path"):
            data["install_path"] = Path(data["install_path"])
        return cls(**data)


class PluginMarket:
    """插件市场."""

    CATEGORIES: dict[str, str] = {
        "filter": "滤镜/处理",
        "export": "导出格式",
        "ai": "AI增强",
        "utility": "实用工具",
        "integration": "外部集成",
    }

    def __init__(self, market_dir: Path | None = None) -> None:
        self.market_dir = market_dir or Path.home() / ".bitmap_vector_studio" / "plugin_market"
        self.market_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.market_dir / "index.json"
        self.ratings_file = self.market_dir / "ratings.json"
        self._index: list[PluginPackage] = []
        self._ratings: dict[str, dict[str, int]] = {}
        self._load_index()
        self._load_ratings()

    def _load_index(self) -> None:
        if self.index_file.exists():
            try:
                data = json.loads(self.index_file.read_text(encoding="utf-8"))
                self._index = [PluginPackage.from_dict(item) for item in data]
            except Exception:
                self._index = []

    def _save_index(self) -> None:
        self.index_file.write_text(
            json.dumps([p.to_dict() for p in self._index], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _load_ratings(self) -> None:
        if self.ratings_file.exists():
            try:
                self._ratings = json.loads(self.ratings_file.read_text(encoding="utf-8"))
            except Exception:
                self._ratings = {}

    def _save_ratings(self) -> None:
        self.ratings_file.write_text(
            json.dumps(self._ratings, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def discover_plugins(
        self,
        query: str | None = None,
        category: str | None = None,
        sort_by: str = "rating",
    ) -> list[PluginPackage]:
        """发现插件."""
        results = self._index.copy()
        if query:
            q = query.lower()
            results = [
                p
                for p in results
                if q in p.name.lower()
                or q in p.description.lower()
                or any(q in t.lower() for t in p.tags)
            ]
        if category:
            results = [p for p in results if p.category == category]

        sort_key = {
            "rating": lambda p: (-p.rating, -p.downloads),
            "downloads": lambda p: (-p.downloads, -p.rating),
            "name": lambda p: p.name.lower(),
            "newest": lambda p: p.name.lower(),  # 简化
        }.get(sort_by, lambda p: (-p.rating, -p.downloads))

        return sorted(results, key=sort_key)

    def get_categories(self) -> dict[str, int]:
        """获取分类统计."""
        counts: dict[str, int] = {}
        for p in self._index:
            counts[p.category] = counts.get(p.category, 0) + 1
        return counts

    def rate_plugin(self, package_id: str, user_id: str, rating: int) -> bool:
        """评分插件."""
        if not 1 <= rating <= 5:
            return False
        if package_id not in self._ratings:
            self._ratings[package_id] = {}
        self._ratings[package_id][user_id] = rating
        self._save_ratings()

        # 更新平均分
        for p in self._index:
            if p.package_id == package_id:
                ratings = list(self._ratings.get(package_id, {}).values())
                p.rating = sum(ratings) / len(ratings) if ratings else 0.0
                break
        self._save_index()
        return True

    def install_plugin(self, package_id: str, source_path: Path) -> bool:
        """安装插件."""
        for p in self._index:
            if p.package_id == package_id:
                p.installed = True
                p.install_path = source_path
                break
        self._save_index()
        return True

    def uninstall_plugin(self, package_id: str) -> bool:
        """卸载插件."""
        for p in self._index:
            if p.package_id == package_id:
                p.installed = False
                p.enabled = False
                p.install_path = None
                break
        self._save_index()
        return True

    def publish_plugin(self, package: PluginPackage) -> str:
        """发布插件."""
        self._index.append(package)
        self._save_index()
        return package.package_id

    def get_plugin(self, package_id: str) -> PluginPackage | None:
        """获取单个插件信息."""
        for p in self._index:
            if p.package_id == package_id:
                return p
        return None
