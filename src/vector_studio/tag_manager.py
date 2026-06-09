"""文件标签管理系统.

支持为文件添加标签、分类、智能标签推荐.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class TagManager:
    """标签管理器."""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or Path.home() / ".bitmap_vector_studio"
        self.tag_file = self.data_dir / "tags.json"
        self._tags: dict[str, list[str]] = {}  # file_path -> [tags]
        self._load()

    def _load(self) -> None:
        if self.tag_file.exists():
            try:
                self._tags = json.loads(self.tag_file.read_text(encoding="utf-8"))
            except Exception:
                self._tags = {}

    def _save(self) -> None:
        self.tag_file.parent.mkdir(parents=True, exist_ok=True)
        self.tag_file.write_text(
            json.dumps(self._tags, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def add_tag(self, file_path: str, tag: str) -> None:
        """为文件添加标签."""
        if file_path not in self._tags:
            self._tags[file_path] = []
        if tag not in self._tags[file_path]:
            self._tags[file_path].append(tag)
            self._save()

    def remove_tag(self, file_path: str, tag: str) -> None:
        """移除文件标签."""
        if file_path in self._tags and tag in self._tags[file_path]:
            self._tags[file_path].remove(tag)
            if not self._tags[file_path]:
                del self._tags[file_path]
            self._save()

    def get_tags(self, file_path: str) -> list[str]:
        """获取文件标签."""
        return self._tags.get(file_path, []).copy()

    def list_all_tags(self) -> list[str]:
        """列出所有标签."""
        tags: set[str] = set()
        for file_tags in self._tags.values():
            tags.update(file_tags)
        return sorted(tags)

    def search_by_tag(self, tag: str) -> list[str]:
        """按标签搜索文件."""
        return [path for path, tags in self._tags.items() if tag in tags]

    def suggest_tags(self, file_path: str, preset: str | None = None) -> list[str]:
        """智能推荐标签.

        基于文件特征和预设推荐标签.
        """
        suggestions: list[str] = []

        # 基于文件扩展名
        ext = Path(file_path).suffix.lower()
        if ext in (".png", ".jpg", ".jpeg"):
            suggestions.append("photo")
        elif ext == ".svg":
            suggestions.append("vector")

        # 基于预设
        if preset:
            preset_tags = {
                "logo": ["logo", "branding"],
                "poster": ["poster", "illustration"],
                "bw": ["monochrome", "line-art"],
                "photo": ["photo", "realistic"],
                "pixel_art": ["pixel", "retro"],
            }
            suggestions.extend(preset_tags.get(preset, []))

        # 去重并过滤已存在的
        existing = set(self.get_tags(file_path))
        return [t for t in suggestions if t not in existing]

    def auto_tag(self, file_path: str, preset: str | None = None) -> list[str]:
        """自动标签."""
        suggestions = self.suggest_tags(file_path, preset)
        for tag in suggestions:
            self.add_tag(file_path, tag)
        return suggestions
