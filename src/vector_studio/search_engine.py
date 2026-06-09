"""高级搜索与过滤引擎.

支持历史记录、文件、预设的多维度搜索.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class SearchResult:
    """搜索结果."""

    item: Any
    score: float
    matched_fields: list[str]


class SearchEngine:
    """搜索引擎."""

    def __init__(self) -> None:
        self._index: list[tuple[Any, dict[str, str]]] = []

    def add(self, item: Any, fields: dict[str, str]) -> None:
        """添加索引项.

        Args:
            item: 原始对象
            fields: 可搜索字段 {field_name: text}
        """
        self._index.append((item, fields))

    def clear(self) -> None:
        """清空索引."""
        self._index.clear()

    def search(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
    ) -> list[SearchResult]:
        """搜索.

        Args:
            query: 搜索关键词
            filters: 过滤条件 {field: value}
            limit: 最大结果数

        Returns:
            按相关性排序的结果列表
        """
        if not query and not filters:
            return []

        query_lower = query.lower()
        results: list[SearchResult] = []

        for item, fields in self._index:
            # 过滤检查
            if filters:
                skip = False
                for field, value in filters.items():
                    if field not in fields or fields[field] != str(value):
                        skip = True
                        break
                if skip:
                    continue

            # 搜索匹配
            if not query:
                results.append(SearchResult(item, 1.0, []))
                continue

            score = 0.0
            matched: list[str] = []

            for field, text in fields.items():
                text_lower = text.lower()

                # 完全匹配得分最高
                if query_lower == text_lower:
                    score += 10.0
                    matched.append(field)
                # 开头匹配
                elif text_lower.startswith(query_lower):
                    score += 5.0
                    matched.append(field)
                # 单词匹配
                elif any(query_lower == word for word in text_lower.split()):
                    score += 3.0
                    matched.append(field)
                # 包含匹配
                elif query_lower in text_lower:
                    score += 2.0
                    matched.append(field)

            if score > 0:
                results.append(SearchResult(item, score, matched))

        # 按得分排序
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def fuzzy_search(self, query: str, limit: int = 20) -> list[SearchResult]:
        """模糊搜索（支持拼写错误）."""
        results: list[SearchResult] = []
        query_lower = query.lower()

        for item, fields in self._index:
            best_score = 0.0
            matched: list[str] = []

            for field, text in fields.items():
                text_lower = text.lower()
                # 计算相似度
                score = self._similarity(query_lower, text_lower)
                if score > 0.5:  # 阈值
                    best_score = max(best_score, score)
                    matched.append(field)

            if best_score > 0:
                results.append(SearchResult(item, best_score, matched))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        """计算字符串相似度 (0-1)."""
        # 使用Jaccard相似度
        set_a = set(a)
        set_b = set(b)
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union


class HistorySearch:
    """历史记录搜索."""

    def __init__(self, history_dir: Path | None = None) -> None:
        self.history_dir = history_dir or Path.home() / ".bitmap_vector_studio"
        self.engine = SearchEngine()
        self._build_index()

    def _build_index(self) -> None:
        """构建历史记录索引."""
        history_file = self.history_dir / "history.jsonl"
        if not history_file.exists():
            return

        for line in history_file.read_text(encoding="utf-8").strip().split("\n"):
            try:
                item = json.loads(line)
                self.engine.add(
                    item,
                    {
                        "file_name": Path(item.get("input_path", "")).name,
                        "preset": item.get("preset_name", ""),
                        "status": "completed" if item.get("output_path") else "failed",
                        "timestamp": item.get("timestamp", ""),
                        "engine": item.get("engine", ""),
                    },
                )
            except json.JSONDecodeError:
                continue

    def search(
        self,
        query: str,
        status: str | None = None,
        preset: str | None = None,
        limit: int = 20,
    ) -> list[SearchResult]:
        """搜索历史记录."""
        filters: dict[str, Any] = {}
        if status:
            filters["status"] = status
        if preset:
            filters["preset"] = preset

        return self.engine.search(query, filters, limit)

    def refresh(self) -> None:
        """刷新索引."""
        self.engine.clear()
        self._build_index()
