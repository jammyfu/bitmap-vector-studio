from __future__ import annotations

import ast
import importlib.util
import inspect
import json
import re
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any

from PIL import Image

from .models import TraceOptions, TraceResult
from .plugin_interface import Plugin


class PluginValidator:
    """Validate plugin files for correctness and safety."""

    DANGEROUS_CALLS: tuple[str, ...] = (
        "os.system",
        "os.popen",
        "os.spawn",
        "subprocess.call",
        "subprocess.run",
        "subprocess.Popen",
        "eval",
        "exec",
        "compile",
        "__import__",
        "importlib.import_module",
    )

    REQUIRED_ATTRS: tuple[str, ...] = ("name", "version", "description")

    @classmethod
    def validate(cls, plugin_path: Path) -> tuple[bool, list[str]]:
        """Validate a single plugin file.

        Parameters
        ----------
        plugin_path:
            Path to the ``.py`` plugin file.

        Returns
        -------
        tuple[bool, list[str]]
            ``(passed, errors)`` where *errors* is a list of human-readable
            validation messages.
        """
        errors: list[str] = []
        path = Path(plugin_path)

        if not path.exists():
            return False, [f"File not found: {path}"]

        if path.suffix != ".py":
            return False, [f"Not a Python file: {path}"]

        # AST-level checks (syntax + dangerous calls)
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except SyntaxError as exc:
            return False, [f"Syntax error: {exc}"]
        except Exception as exc:
            return False, [f"Failed to read file: {exc}"]

        dangerous = cls._find_dangerous_calls(tree)
        if dangerous:
            errors.append(f"Dangerous calls detected: {', '.join(dangerous)}")

        # Runtime import checks
        try:
            classes = cls._load_plugin_classes(path)
        except Exception as exc:
            errors.append(f"Import failed: {exc}")
            return False, errors

        if not classes:
            errors.append("No Plugin subclass found.")
            return False, errors

        for cls_obj in classes:
            for attr in cls.REQUIRED_ATTRS:
                if not getattr(cls_obj, attr, None):
                    errors.append(f"Class '{cls_obj.__name__}' missing required attribute '{attr}'.")

            # Hook signature checks
            for hook in ("preprocess", "postprocess", "on_convert_complete"):
                method = getattr(cls_obj, hook, None)
                if method is None:
                    continue
                if method is getattr(Plugin, hook, None):
                    continue
                try:
                    sig = inspect.signature(method)
                except ValueError:
                    continue
                params = list(sig.parameters.keys())
                expected = ["self"]
                if hook == "preprocess":
                    expected += ["image", "options"]
                elif hook == "postprocess":
                    expected += ["svg_path", "options"]
                elif hook == "on_convert_complete":
                    expected += ["result", "options"]
                if params != expected:
                    errors.append(
                        f"Class '{cls_obj.__name__}' hook '{hook}' has unexpected signature {params}, expected {expected}."
                    )

        passed = not errors
        return passed, errors

    @classmethod
    def validate_batch(cls, plugin_dir: Path) -> list[dict[str, Any]]:
        """Validate every ``.py`` file in *plugin_dir*.

        Returns
        -------
        list[dict]
            One dict per file with keys ``path``, ``passed``, ``errors``.
        """
        results: list[dict[str, Any]] = []
        directory = Path(plugin_dir)
        if not directory.is_dir():
            return [{"path": str(directory), "passed": False, "errors": ["Not a directory."]}]
        for py_file in sorted(directory.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            passed, errors = cls.validate(py_file)
            results.append({"path": str(py_file), "passed": passed, "errors": errors})
        return results

    @staticmethod
    def _load_plugin_classes(path: Path) -> list[type[Plugin]]:
        """Dynamically import *path* and return concrete Plugin subclasses."""
        module_name = f"_plugin_sdk_validate_{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot create module spec for {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        classes: list[type[Plugin]] = []
        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, Plugin) and obj is not Plugin and obj.name:
                classes.append(obj)
        return classes

    @classmethod
    def _find_dangerous_calls(cls, tree: ast.AST) -> list[str]:
        """Scan AST for dangerous function calls."""
        found: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call_name = cls._get_call_name(node.func)
                if call_name and call_name in cls.DANGEROUS_CALLS:
                    found.append(call_name)
        return sorted(set(found))

    @staticmethod
    def _get_call_name(node: ast.expr) -> str | None:
        """Return the dotted name of a call expression, e.g. ``os.system``."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parts: list[str] = []
            current: ast.expr = node
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        return None


class PluginDebugger:
    """Test and profile plugins in isolation."""

    @classmethod
    def test_plugin(cls, plugin_path: Path) -> dict[str, Any]:
        """Run a plugin through all hooks in an isolated environment.

        Parameters
        ----------
        plugin_path:
            Path to the ``.py`` plugin file.

        Returns
        -------
        dict
            Keys: ``passed`` (bool), ``hook_results`` (dict), ``total_seconds`` (float),
            ``errors`` (list[str]).
        """
        errors: list[str] = []
        hook_results: dict[str, str] = {}
        start = time.perf_counter()

        try:
            classes = PluginValidator._load_plugin_classes(plugin_path)
        except Exception as exc:
            return {"passed": False, "hook_results": {}, "total_seconds": 0.0, "errors": [str(exc)]}

        if not classes:
            return {"passed": False, "hook_results": {}, "total_seconds": 0.0, "errors": ["No Plugin subclass found."]}

        inst = classes[0]()
        options: dict[str, Any] = {}

        # preprocess
        if hasattr(type(inst), "preprocess") and type(inst).preprocess is not Plugin.preprocess:
            try:
                img = Image.new("RGB", (10, 10), color=(255, 0, 0))
                result = inst.preprocess(img, options)
                if not isinstance(result, Image.Image):
                    errors.append("preprocess did not return a PIL Image.")
                else:
                    hook_results["preprocess"] = "ok"
            except Exception as exc:
                errors.append(f"preprocess failed: {exc}")
                hook_results["preprocess"] = "failed"
        else:
            hook_results["preprocess"] = "skipped"

        # postprocess
        if hasattr(type(inst), "postprocess") and type(inst).postprocess is not Plugin.postprocess:
            try:
                svg = Path("/tmp/_plugin_debug_test.svg")
                # Use a temp path if possible, otherwise fallback
                import tempfile
                with tempfile.TemporaryDirectory() as td:
                    svg = Path(td) / "test.svg"
                    svg.write_text('<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"></svg>', encoding="utf-8")
                    result = inst.postprocess(svg, options)
                    if not isinstance(result, Path):
                        errors.append("postprocess did not return a Path.")
                    else:
                        hook_results["postprocess"] = "ok"
            except Exception as exc:
                errors.append(f"postprocess failed: {exc}")
                hook_results["postprocess"] = "failed"
        else:
            hook_results["postprocess"] = "skipped"

        # on_convert_complete
        if hasattr(type(inst), "on_convert_complete") and type(inst).on_convert_complete is not Plugin.on_convert_complete:
            try:
                mock_result = TraceResult(
                    input_path=Path("/tmp/in.png"),
                    svg_path=Path("/tmp/out.svg"),
                    engine="test",
                    elapsed_seconds=0.0,
                )
                inst.on_convert_complete(mock_result, options)
                hook_results["on_convert_complete"] = "ok"
            except Exception as exc:
                errors.append(f"on_convert_complete failed: {exc}")
                hook_results["on_convert_complete"] = "failed"
        else:
            hook_results["on_convert_complete"] = "skipped"

        total = time.perf_counter() - start
        return {
            "passed": not errors,
            "hook_results": hook_results,
            "total_seconds": round(total, 4),
            "errors": errors,
        }

    @classmethod
    def profile_plugin(cls, plugin_path: Path) -> dict[str, Any]:
        """Profile hook execution time and peak memory.

        Returns
        -------
        dict
            Keys: ``hook_times`` (dict[str, float]), ``peak_memory_kb`` (float),
            ``errors`` (list[str]).
        """
        errors: list[str] = []
        hook_times: dict[str, float] = {}

        try:
            classes = PluginValidator._load_plugin_classes(plugin_path)
        except Exception as exc:
            return {"hook_times": {}, "peak_memory_kb": 0.0, "errors": [str(exc)]}

        if not classes:
            return {"hook_times": {}, "peak_memory_kb": 0.0, "errors": ["No Plugin subclass found."]}

        inst = classes[0]()
        options: dict[str, Any] = {}

        tracemalloc.start()

        # preprocess
        if hasattr(type(inst), "preprocess") and type(inst).preprocess is not Plugin.preprocess:
            img = Image.new("RGB", (100, 100), color=(255, 0, 0))
            t0 = time.perf_counter()
            try:
                inst.preprocess(img, options)
                hook_times["preprocess"] = round(time.perf_counter() - t0, 6)
            except Exception as exc:
                errors.append(f"preprocess failed: {exc}")
                hook_times["preprocess"] = -1.0
        else:
            hook_times["preprocess"] = 0.0

        # postprocess
        if hasattr(type(inst), "postprocess") and type(inst).postprocess is not Plugin.postprocess:
            import tempfile
            with tempfile.TemporaryDirectory() as td:
                svg = Path(td) / "test.svg"
                svg.write_text('<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"></svg>', encoding="utf-8")
                t0 = time.perf_counter()
                try:
                    inst.postprocess(svg, options)
                    hook_times["postprocess"] = round(time.perf_counter() - t0, 6)
                except Exception as exc:
                    errors.append(f"postprocess failed: {exc}")
                    hook_times["postprocess"] = -1.0
        else:
            hook_times["postprocess"] = 0.0

        # on_convert_complete
        if hasattr(type(inst), "on_convert_complete") and type(inst).on_convert_complete is not Plugin.on_convert_complete:
            mock_result = TraceResult(
                input_path=Path("/tmp/in.png"),
                svg_path=Path("/tmp/out.svg"),
                engine="test",
                elapsed_seconds=0.0,
            )
            t0 = time.perf_counter()
            try:
                inst.on_convert_complete(mock_result, options)
                hook_times["on_convert_complete"] = round(time.perf_counter() - t0, 6)
            except Exception as exc:
                errors.append(f"on_convert_complete failed: {exc}")
                hook_times["on_convert_complete"] = -1.0
        else:
            hook_times["on_convert_complete"] = 0.0

        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        return {
            "hook_times": hook_times,
            "peak_memory_kb": round(peak / 1024, 2),
            "errors": errors,
        }


class PluginScaffold:
    """Generate boiler-plate code for new plugins."""

    BUILTIN_TEMPLATES: dict[str, str] = {
        "watermark": """\
from __future__ import annotations

from pathlib import Path
from typing import Any

from vector_studio.plugin_interface import Plugin


class {class_name}(Plugin):
    \"\"\"Add a watermark to generated SVGs.\"\"\"

    name = "{plugin_name}"
    version = "1.0.0"
    description = "Add a watermark to generated SVGs."
    author = ""

    def postprocess(self, svg_path: Path, options: dict[str, Any]) -> Path:
        \"\"\"Inject watermark into the SVG.\"\"\"
        text = options.get("watermark_text", "Watermark")
        content = svg_path.read_text(encoding="utf-8")
        if "</svg>" in content:
            content = content.replace("</svg>", f'<text x="10" y="20">{{text}}</text></svg>', 1)
        svg_path.write_text(content, encoding="utf-8")
        return svg_path
""",
        "resize": """\
from __future__ import annotations

from pathlib import Path
from typing import Any

from vector_studio.plugin_interface import Plugin


class {class_name}(Plugin):
    \"\"\"Resize SVG dimensions after conversion.\"\"\"

    name = "{plugin_name}"
    version = "1.0.0"
    description = "Resize SVG dimensions after conversion."
    author = ""

    def postprocess(self, svg_path: Path, options: dict[str, Any]) -> Path:
        \"\"\"Scale width/height attributes.\"\"\"
        scale = options.get("resize_scale", 1.0)
        # TODO: implement scaling logic
        return svg_path
""",
        "filter": """\
from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

from vector_studio.plugin_interface import Plugin


class {class_name}(Plugin):
    \"\"\"Apply a filter to the input image before tracing.\"\"\"

    name = "{plugin_name}"
    version = "1.0.0"
    description = "Apply a filter to the input image before tracing."
    author = ""

    def preprocess(self, image: Image.Image, options: dict[str, Any]) -> Image.Image:
        \"\"\"Apply image filter.\"\"\"
        # TODO: implement filter logic
        return image
""",
        "annotate": """\
from __future__ import annotations

from pathlib import Path
from typing import Any

from vector_studio.plugin_interface import Plugin
from vector_studio.models import TraceResult


class {class_name}(Plugin):
    \"\"\"Annotate the output after conversion completes.\"\"\"

    name = "{plugin_name}"
    version = "1.0.0"
    description = "Annotate the output after conversion completes."
    author = ""

    def on_convert_complete(self, result: TraceResult, options: dict[str, Any]) -> None:
        \"\"\"Log or annotate the conversion result.\"\"\"
        # TODO: implement annotation logic
        pass
""",
    }

    @classmethod
    def generate(
        cls,
        name: str,
        output_dir: Path,
        hooks: list[str] | None = None,
    ) -> Path:
        """Generate a new plugin template.

        Parameters
        ----------
        name:
            Plugin name (kebab-case recommended).
        output_dir:
            Directory where the plugin file and test file will be written.
        hooks:
            List of hooks to implement: ``preprocess``, ``postprocess``,
            ``on_convert_complete``.  Defaults to ``postprocess`` only.

        Returns
        -------
        Path
            Path to the generated plugin file.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "", name)
        class_name = "".join(part.capitalize() for part in safe_name.replace("-", "_").split("_")) + "Plugin"
        file_name = safe_name.replace("-", "_") + "_plugin.py"
        plugin_file = output_dir / file_name

        hooks = hooks or ["postprocess"]
        hook_impls = cls._build_hook_impls(hooks)

        content = f'''\
from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

from vector_studio.plugin_interface import Plugin
from vector_studio.models import TraceResult


class {class_name}(Plugin):
    """{name} plugin for Bitmap Vector Studio."""

    name = "{safe_name}"
    version = "1.0.0"
    description = "Auto-generated {name} plugin."
    author = ""

{hook_impls}
'''
        plugin_file.write_text(content, encoding="utf-8")

        # Generate a minimal test file
        test_file = output_dir / f"test_{safe_name.replace('-', '_')}_plugin.py"
        test_content = f'''\
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from vector_studio.plugin_interface import Plugin
from vector_studio.models import TraceResult

# Import the generated plugin (adjust import path as needed)
# from {safe_name.replace("-", "_")}_plugin import {class_name}


class Test{class_name}:
    def test_plugin_inherits_base(self):
        # plugin = {class_name}()
        # assert isinstance(plugin, Plugin)
        pass

    def test_preprocess_hook(self, tmp_path: Path):
        # plugin = {class_name}()
        # img = Image.new("RGB", (10, 10))
        # result = plugin.preprocess(img, {{}})
        # assert isinstance(result, Image.Image)
        pass
'''
        test_file.write_text(test_content, encoding="utf-8")
        return plugin_file

    @classmethod
    def generate_from_template(cls, template: str, name: str, output_dir: Path) -> Path:
        """Generate a plugin from a built-in template.

        Parameters
        ----------
        template:
            One of ``watermark``, ``resize``, ``filter``, ``annotate``.
        name:
            Plugin name.
        output_dir:
            Destination directory.

        Returns
        -------
        Path
            Path to the generated plugin file.

        Raises
        ------
        ValueError
            If *template* is not a known built-in template.
        """
        if template not in cls.BUILTIN_TEMPLATES:
            valid = ", ".join(sorted(cls.BUILTIN_TEMPLATES))
            raise ValueError(f"Unknown template '{template}'. Valid templates: {valid}.")

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "", name)
        class_name = "".join(part.capitalize() for part in safe_name.replace("-", "_").split("_")) + "Plugin"
        file_name = safe_name.replace("-", "_") + "_plugin.py"
        plugin_file = output_dir / file_name

        tpl = cls.BUILTIN_TEMPLATES[template]
        content = tpl.format(class_name=class_name, plugin_name=safe_name)
        plugin_file.write_text(content, encoding="utf-8")
        return plugin_file

    @staticmethod
    def _build_hook_impls(hooks: list[str]) -> str:
        """Build method stubs for the requested hooks."""
        lines: list[str] = []
        if "preprocess" in hooks:
            lines.append('    def preprocess(self, image: Image.Image, options: dict[str, Any]) -> Image.Image:')
            lines.append('        """Pre-process the input image."""')
            lines.append('        # TODO: implement preprocessing logic')
            lines.append('        return image')
            lines.append('')
        if "postprocess" in hooks:
            lines.append('    def postprocess(self, svg_path: Path, options: dict[str, Any]) -> Path:')
            lines.append('        """Post-process the generated SVG."""')
            lines.append('        # TODO: implement postprocessing logic')
            lines.append('        return svg_path')
            lines.append('')
        if "on_convert_complete" in hooks:
            lines.append('    def on_convert_complete(self, result: TraceResult, options: dict[str, Any]) -> None:')
            lines.append('        """Handle conversion completion."""')
            lines.append('        # TODO: implement completion logic')
            lines.append('        pass')
            lines.append('')
        return "\n".join(lines)


class PluginDocsGenerator:
    """Generate documentation for plugins."""

    @staticmethod
    def generate_readme(plugin_path: Path) -> str:
        """Generate a README markdown string for a single plugin.

        Parameters
        ----------
        plugin_path:
            Path to the plugin ``.py`` file.

        Returns
        -------
        str
            Markdown README content.
        """
        path = Path(plugin_path)
        try:
            classes = PluginValidator._load_plugin_classes(path)
        except Exception as exc:
            return f"# Plugin Documentation\n\nError loading plugin: {exc}\n"

        if not classes:
            return "# Plugin Documentation\n\nNo Plugin subclass found.\n"

        cls_obj = classes[0]
        inst = cls_obj()
        hooks = []
        for hook in ("preprocess", "postprocess", "on_convert_complete"):
            method = getattr(type(inst), hook, None)
            if method is not None and method is not getattr(Plugin, hook, None):
                hooks.append(hook)

        lines = [
            f"# {cls_obj.name or 'Unknown Plugin'}",
            "",
            f"**Version:** {cls_obj.version or 'N/A'}",
            "",
            f"**Author:** {cls_obj.author or 'N/A'}",
            "",
            f"{cls_obj.description or 'No description provided.'}",
            "",
            "## Hooks",
            "",
        ]
        if hooks:
            for hook in hooks:
                lines.append(f"- `{hook}`")
        else:
            lines.append("- None (no hooks implemented)")
        lines.append("")
        lines.append("## Usage")
        lines.append("")
        lines.append("Enable the plugin via CLI:")
        lines.append(f"```bash")
        lines.append(f"vector-studio trace input.png --plugin {cls_obj.name}")
        lines.append("```")
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def generate_api_docs(plugin_dir: Path) -> str:
        """Generate API documentation for all plugins in a directory.

        Parameters
        ----------
        plugin_dir:
            Directory containing ``.py`` plugin files.

        Returns
        -------
        str
            Markdown API documentation.
        """
        directory = Path(plugin_dir)
        lines = ["# Plugin API Documentation", ""]
        if not directory.is_dir():
            lines.append(f"*Directory not found: {directory}*")
            return "\n".join(lines)

        for py_file in sorted(directory.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            try:
                classes = PluginValidator._load_plugin_classes(py_file)
            except Exception as exc:
                lines.append(f"## {py_file.name}")
                lines.append(f"\n*Load error: {exc}*\n")
                continue

            for cls_obj in classes:
                inst = cls_obj()
                hooks = []
                for hook in ("preprocess", "postprocess", "on_convert_complete"):
                    method = getattr(type(inst), hook, None)
                    if method is not None and method is not getattr(Plugin, hook, None):
                        doc = (method.__doc__ or "").strip()
                        hooks.append(f"`{hook}` — {doc}" if doc else f"`{hook}`")
                lines.append(f"## {cls_obj.name or cls_obj.__name__}")
                lines.append("")
                lines.append(f"- **File:** `{py_file.name}`")
                lines.append(f"- **Version:** {cls_obj.version or 'N/A'}")
                lines.append(f"- **Author:** {cls_obj.author or 'N/A'}")
                lines.append(f"- **Description:** {cls_obj.description or 'N/A'}")
                lines.append("")
                lines.append("### Hooks")
                lines.append("")
                if hooks:
                    for hook in hooks:
                        lines.append(f"- {hook}")
                else:
                    lines.append("- None")
                lines.append("")
        return "\n".join(lines)


class PluginSDK:
    """插件开发SDK.

    提供插件开发所需的工具、验证器、脚手架生成器.
    """

    PLUGIN_TEMPLATE = '''\
"""{name} Plugin for Bitmap Vector Studio.

Author: {author}
Version: {version}
Description: {description}
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image

from vector_studio.plugin_interface import Plugin


class {class_name}(Plugin):
    name = "{package_id}"
    version = "{version}"
    description = "{description}"
    author = "{author}"

    def preprocess(self, image: Image.Image, options: dict[str, Any]) -> Image.Image:
        """在矢量化之前处理图片."""
        # TODO: 实现预处理逻辑
        return image

    def postprocess(self, svg_path: Path, options: dict[str, Any]) -> Path:
        """在SVG优化后处理输出."""
        # TODO: 实现后处理逻辑
        return svg_path

    def on_convert_complete(self, result: Any, options: dict[str, Any]) -> None:
        """在转换完成后执行."""
        # TODO: 实现完成回调
        pass
'''

    def __init__(self, output_dir: Path | None = None) -> None:
        self.output_dir = output_dir or Path.cwd()

    def scaffold(
        self,
        name: str,
        author: str,
        description: str,
        version: str = "1.0.0",
    ) -> Path:
        """生成插件脚手架."""
        package_id = name.lower().replace(" ", "_")
        class_name = "".join(w.capitalize() for w in name.split())

        plugin_dir = self.output_dir / f"{package_id}_plugin"
        plugin_dir.mkdir(exist_ok=True)

        # 主文件
        main_file = plugin_dir / f"{package_id}.py"
        main_file.write_text(
            self.PLUGIN_TEMPLATE.format(
                name=name,
                package_id=package_id,
                class_name=class_name,
                author=author,
                description=description,
                version=version,
            ),
            encoding="utf-8",
        )

        # 测试文件
        test_file = plugin_dir / f"test_{package_id}.py"
        test_file.write_text(
            f'''import pytest
from pathlib import Path
from PIL import Image
from {package_id} import {class_name}


@pytest.fixture
def plugin():
    return {class_name}()


def test_preprocess(plugin):
    img = Image.new('RGB', (100, 100), color='red')
    result = plugin.preprocess(img, {{}})
    assert result is not None


def test_postprocess(plugin, tmp_path):
    svg = tmp_path / "test.svg"
    svg.write_text("<svg></svg>")
    result = plugin.postprocess(svg, {{}})
    assert result is not None
''',
            encoding="utf-8",
        )

        # README
        readme = plugin_dir / "README.md"
        readme.write_text(
            f"""# {name} Plugin

{description}

## 安装

```bash
vector-studio plugin install {plugin_dir}/{package_id}.py
```

## 使用

```bash
vector-studio trace input.png --plugin {package_id}
```
""",
            encoding="utf-8",
        )

        # manifest
        manifest = plugin_dir / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "name": name,
                    "package_id": package_id,
                    "version": version,
                    "description": description,
                    "author": author,
                    "category": "utility",
                    "tags": [],
                    "dependencies": [],
                    "min_app_version": "3.0.0",
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        return plugin_dir

    def validate(self, plugin_path: Path) -> dict[str, Any]:
        """验证插件."""
        errors: list[str] = []
        warnings: list[str] = []

        if not plugin_path.exists():
            return {"valid": False, "errors": ["文件不存在"], "warnings": []}

        # 检查基本结构
        content = plugin_path.read_text(encoding="utf-8")

        if "class" not in content:
            errors.append("未找到类定义")
        if "Plugin" not in content:
            errors.append("未继承 Plugin 基类")
        if "name" not in content:
            errors.append("未定义 name 属性")

        # 检查manifest
        manifest = plugin_path.parent / "manifest.json"
        if not manifest.exists():
            warnings.append("缺少 manifest.json")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
