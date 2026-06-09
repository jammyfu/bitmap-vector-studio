"""智能批处理规则引擎.

基于规则自动处理文件，支持条件判断和动作执行.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass
class Rule:
    """批处理规则."""

    name: str
    condition: str  # 条件表达式
    action: str  # 动作类型
    action_params: dict[str, Any]
    enabled: bool = True
    priority: int = 0


class RuleEngine:
    """规则引擎."""

    def __init__(self):
        self._rules: list[Rule] = []
        self._actions: dict[str, Callable] = {}
        self._register_default_actions()

    def _register_default_actions(self) -> None:
        """注册默认动作."""
        self._actions["convert"] = self._action_convert
        self._actions["tag"] = self._action_tag
        self._actions["move"] = self._action_move
        self._actions["copy"] = self._action_copy
        self._actions["rename"] = self._action_rename
        self._actions["delete"] = self._action_delete

    def add_rule(self, rule: Rule) -> None:
        """添加规则."""
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority, reverse=True)

    def remove_rule(self, name: str) -> bool:
        """移除规则."""
        for i, r in enumerate(self._rules):
            if r.name == name:
                self._rules.pop(i)
                return True
        return False

    def list_rules(self) -> list[Rule]:
        """列出规则."""
        return self._rules.copy()

    def evaluate(
        self, file_path: Path, context: dict[str, Any] | None = None
    ) -> list[tuple[str, bool, str]]:
        """评估文件并执行匹配的规则.

        Returns:
            列表 of (rule_name, success, message)
        """
        results = []
        ctx = context or {}
        ctx["file"] = file_path
        ctx["name"] = file_path.name
        ctx["stem"] = file_path.stem
        ctx["suffix"] = file_path.suffix.lower()
        ctx["size"] = file_path.stat().st_size if file_path.exists() else 0

        for rule in self._rules:
            if not rule.enabled:
                continue

            if self._check_condition(rule.condition, ctx):
                try:
                    action_fn = self._actions.get(rule.action)
                    if action_fn:
                        action_fn(ctx, rule.action_params)
                        results.append((rule.name, True, "executed"))
                    else:
                        results.append(
                            (rule.name, False, f"未知动作: {rule.action}")
                        )
                except Exception as e:
                    results.append((rule.name, False, str(e)))

        return results

    def _check_condition(self, condition: str, ctx: dict) -> bool:
        """检查条件.

        支持的条件语法:
        - suffix == '.png'
        - size > 1000000
        - name contains 'logo'
        - suffix in ['.png', '.jpg']
        """
        try:
            # 简单条件解析
            if "==" in condition:
                field, value = condition.split("==", 1)
                field = field.strip()
                value = value.strip().strip("'\"")
                return str(ctx.get(field, "")) == value

            elif ">" in condition:
                field, value = condition.split(">", 1)
                field = field.strip()
                value = float(value.strip())
                return float(ctx.get(field, 0)) > value

            elif "<" in condition:
                field, value = condition.split("<", 1)
                field = field.strip()
                value = float(value.strip())
                return float(ctx.get(field, 0)) < value

            elif "contains" in condition:
                field, value = condition.split("contains", 1)
                field = field.strip()
                value = value.strip().strip("'\"")
                return value in str(ctx.get(field, ""))

            elif " in " in condition:
                field, value = condition.split(" in ", 1)
                field = field.strip()
                value = eval(value.strip())
                return str(ctx.get(field, "")) in value

            return False
        except Exception:
            return False

    def _action_convert(self, ctx: dict, params: dict) -> None:
        """转换动作."""
        from .tracer import trace_image
        from .presets import options_from_preset

        input_path = ctx["file"]
        output_path = Path(params.get("output_dir", ".")) / f"{input_path.stem}.svg"
        preset = params.get("preset", "poster")

        trace_image(input_path, output_path, options=options_from_preset(preset))

    def _action_tag(self, ctx: dict, params: dict) -> None:
        """标签动作."""
        from .tag_manager import TagManager

        tm = TagManager()
        for tag in params.get("tags", []):
            tm.add_tag(str(ctx["file"]), tag)

    def _action_move(self, ctx: dict, params: dict) -> None:
        """移动动作."""
        import shutil

        dest = Path(params["dest"]) / ctx["file"].name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(ctx["file"]), str(dest))

    def _action_copy(self, ctx: dict, params: dict) -> None:
        """复制动作."""
        import shutil

        dest = Path(params["dest"]) / ctx["file"].name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(ctx["file"]), str(dest))

    def _action_rename(self, ctx: dict, params: dict) -> None:
        """重命名动作."""
        pattern = params.get("pattern", "{stem}_converted{suffix}")
        new_name = pattern.format(
            stem=ctx["stem"],
            suffix=ctx["suffix"],
            name=ctx["name"],
        )
        new_path = ctx["file"].parent / new_name
        ctx["file"].rename(new_path)
        ctx["file"] = new_path

    def _action_delete(self, ctx: dict, params: dict) -> None:
        """删除动作."""
        ctx["file"].unlink()
