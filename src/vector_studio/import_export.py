"""Bitmap Vector Studio 批量导入导出系统.

支持预设、配置、模板、插件、历史记录的导入导出.
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ExportPackage:
    """导出包."""

    version: str
    created_at: str
    items: dict[str, list[dict]]

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "created_at": self.created_at,
            "items": self.items,
        }


class ImportExporter:
    """导入导出器."""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or Path.home() / ".bitmap_vector_studio"

    def export_presets(self, preset_names: list[str] | None = None) -> list[dict]:
        """导出预设."""
        from .preset_manager import get_all_presets, list_user_presets

        user_presets = list_user_presets()
        if preset_names:
            user_presets = {
                k: v for k, v in user_presets.items() if k in preset_names
            }
        # Return list of dicts with name included for portability
        return [
            {"name": name, **entry}
            for name, entry in user_presets.items()
        ]

    def export_config(self) -> dict:
        """导出配置."""
        from .config import Config

        config = Config.load()
        return config.to_dict()

    def export_history(self, limit: int | None = None) -> list[dict]:
        """导出历史记录."""
        from .history import get_recent_tasks

        return get_recent_tasks(limit or 1000)

    def export_templates(self) -> list[dict]:
        """导出模板."""
        from .template_market import TemplateMarket

        market = TemplateMarket()
        templates = market.discover_templates()
        return [t.to_dict() for t in templates]

    def create_package(self, include: list[str] | None = None) -> ExportPackage:
        """创建导出包.

        Args:
            include: 包含的项目 ['presets', 'config', 'history', 'templates']
        """
        include = include or ["presets", "config", "history", "templates"]
        items: dict[str, list[dict]] = {}

        if "presets" in include:
            items["presets"] = self.export_presets()
        if "config" in include:
            items["config"] = [self.export_config()]
        if "history" in include:
            items["history"] = self.export_history()
        if "templates" in include:
            items["templates"] = self.export_templates()

        from . import __version__

        return ExportPackage(
            version=__version__,
            created_at=datetime.now().isoformat(),
            items=items,
        )

    def export_to_json(self, output_path: Path, include: list[str] | None = None) -> Path:
        """导出为JSON文件."""
        package = self.create_package(include)
        output_path.write_text(
            json.dumps(package.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return output_path

    def export_to_zip(self, output_path: Path, include: list[str] | None = None) -> Path:
        """导出为ZIP文件."""
        package = self.create_package(include)

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # 写入元数据
            zf.writestr(
                "manifest.json",
                json.dumps(package.to_dict(), indent=2, ensure_ascii=False),
            )

            # 分别写入各类数据
            for category, items in package.items.items():
                zf.writestr(
                    f"{category}.json",
                    json.dumps(items, indent=2, ensure_ascii=False),
                )

        return output_path

    def import_from_json(
        self, input_path: Path, merge_strategy: str = "merge"
    ) -> dict[str, Any]:
        """从JSON导入.

        Args:
            merge_strategy: 'merge'(合并) / 'replace'(替换) / 'skip'(跳过重复)

        Returns:
            导入结果统计
        """
        data = json.loads(input_path.read_text(encoding="utf-8"))
        package = data if "items" in data else {"items": data, "version": "unknown"}

        stats: dict[str, Any] = {"imported": {}, "errors": []}

        for category, items in package.get("items", {}).items():
            try:
                count = self._import_category(category, items, merge_strategy)
                stats["imported"][category] = count
            except Exception as e:
                stats["errors"].append(f"{category}: {e}")

        return stats

    def import_from_zip(
        self, input_path: Path, merge_strategy: str = "merge"
    ) -> dict[str, Any]:
        """从ZIP导入."""
        with zipfile.ZipFile(input_path, "r") as zf:
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            stats: dict[str, Any] = {"imported": {}, "errors": []}

            for category in manifest.get("items", {}).keys():
                try:
                    items = json.loads(zf.read(f"{category}.json").decode("utf-8"))
                    count = self._import_category(category, items, merge_strategy)
                    stats["imported"][category] = count
                except Exception as e:
                    stats["errors"].append(f"{category}: {e}")

        return stats

    def _import_category(self, category: str, items: list[dict], strategy: str) -> int:
        """导入单个类别."""
        if category == "presets":
            return self._import_presets(items, strategy)
        elif category == "config":
            return self._import_config(items[0] if items else {})
        elif category == "history":
            return self._import_history(items)
        elif category == "templates":
            return self._import_templates(items)
        return 0

    def _import_presets(self, items: list[dict], strategy: str) -> int:
        from .preset_manager import save_preset, list_user_presets

        existing = set(list_user_presets().keys())

        count = 0
        for item in items:
            name = item.get("name")
            if not name:
                continue

            if name in existing:
                if strategy == "skip":
                    continue
                elif strategy == "replace":
                    pass  # 继续保存，覆盖
                # merge: 也继续保存

            try:
                from .models import TraceOptions

                options = TraceOptions(**item.get("options", {}))
                save_preset(name, options, description=item.get("description", ""))
                count += 1
            except Exception:
                continue

        return count

    def _import_config(self, config: dict) -> int:
        from .config import Config

        cfg = Config.from_dict(config)
        cfg.save()
        return 1

    def _import_history(self, items: list[dict]) -> int:
        from .history import _history_path, _ensure_history_dir

        path = _history_path()
        _ensure_history_dir()
        count = 0
        with path.open("a", encoding="utf-8") as f:
            for item in items:
                try:
                    record: dict[str, Any] = {
                        "task_id": item.get("task_id", ""),
                        "timestamp": item.get("timestamp", datetime.now().isoformat()),
                        "input_path": item.get("input_path", ""),
                        "output_path": item.get("output_path", ""),
                        "preset_name": item.get("preset_name", item.get("preset", "default")),
                        "options": item.get("options", {}),
                        "stats": item.get("stats", {}),
                        "engine": item.get("engine", "unknown"),
                        "elapsed_seconds": item.get("elapsed_seconds", 0.0),
                        "export_formats": item.get("export_formats", []),
                    }
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    count += 1
                except Exception:
                    continue
        return count

    def _import_templates(self, items: list[dict]) -> int:
        from .template_market import TemplateMarket, Template

        market = TemplateMarket()
        count = 0
        for item in items:
            try:
                template = Template.from_dict(item)
                market.publish_template(template, "imported")
                count += 1
            except Exception:
                continue
        return count
