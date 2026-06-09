from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from vector_studio.models import TraceResult
from vector_studio.plugin_interface import Plugin
from vector_studio.plugin_sdk import (
    PluginDebugger,
    PluginDocsGenerator,
    PluginScaffold,
    PluginSDK,
    PluginValidator,
)


class TestPluginValidator:
    def test_validator_valid_plugin(self, tmp_path: Path):
        plugin_file = tmp_path / "good_plugin.py"
        plugin_file.write_text(
            "from vector_studio.plugin_interface import Plugin\n"
            "class GoodPlugin(Plugin):\n"
            "    name = 'good'\n"
            "    version = '1.0.0'\n"
            "    description = 'A good plugin'\n"
            "    def preprocess(self, image, options):\n"
            "        return image\n"
        )
        passed, errors = PluginValidator.validate(plugin_file)
        assert passed is True
        assert errors == []

    def test_validator_missing_required_attr(self, tmp_path: Path):
        plugin_file = tmp_path / "bad_plugin.py"
        plugin_file.write_text(
            "from vector_studio.plugin_interface import Plugin\n"
            "class BadPlugin(Plugin):\n"
            "    name = 'bad'\n"
            "    version = '1.0.0'\n"
            "    # missing description\n"
        )
        passed, errors = PluginValidator.validate(plugin_file)
        assert passed is False
        assert any("description" in e for e in errors)

    def test_validator_dangerous_calls(self, tmp_path: Path):
        plugin_file = tmp_path / "dangerous_plugin.py"
        plugin_file.write_text(
            "from vector_studio.plugin_interface import Plugin\n"
            "import os\n"
            "class DangerousPlugin(Plugin):\n"
            "    name = 'dangerous'\n"
            "    version = '1.0.0'\n"
            "    description = 'Bad plugin'\n"
            "    def postprocess(self, svg_path, options):\n"
            "        os.system('rm -rf /')\n"
            "        return svg_path\n"
        )
        passed, errors = PluginValidator.validate(plugin_file)
        assert passed is False
        assert any("os.system" in e for e in errors)

    def test_validator_batch(self, tmp_path: Path):
        good = tmp_path / "good.py"
        good.write_text(
            "from vector_studio.plugin_interface import Plugin\n"
            "class Good(Plugin):\n"
            "    name = 'good'\n"
            "    version = '1.0.0'\n"
            "    description = 'ok'\n"
        )
        bad = tmp_path / "bad.py"
        bad.write_text("this is not valid python !!!")
        results = PluginValidator.validate_batch(tmp_path)
        assert len(results) == 2
        by_name = {Path(r["path"]).name: r for r in results}
        assert by_name["good.py"]["passed"] is True
        assert by_name["bad.py"]["passed"] is False

    def test_validator_wrong_hook_signature(self, tmp_path: Path):
        plugin_file = tmp_path / "sig_plugin.py"
        plugin_file.write_text(
            "from vector_studio.plugin_interface import Plugin\n"
            "class SigPlugin(Plugin):\n"
            "    name = 'sig'\n"
            "    version = '1.0.0'\n"
            "    description = 'sig'\n"
            "    def preprocess(self, image, options, extra):\n"
            "        return image\n"
        )
        passed, errors = PluginValidator.validate(plugin_file)
        assert passed is False
        assert any("preprocess" in e and "signature" in e for e in errors)


class TestPluginDebugger:
    def test_debugger_test_plugin(self, tmp_path: Path):
        plugin_file = tmp_path / "debug_plugin.py"
        plugin_file.write_text(
            "from vector_studio.plugin_interface import Plugin\n"
            "from PIL import Image\n"
            "class DebugPlugin(Plugin):\n"
            "    name = 'debug'\n"
            "    version = '1.0.0'\n"
            "    description = 'debug'\n"
            "    def preprocess(self, image, options):\n"
            "        return image.convert('L')\n"
        )
        result = PluginDebugger.test_plugin(plugin_file)
        assert result["passed"] is True
        assert result["hook_results"]["preprocess"] == "ok"
        assert result["hook_results"]["postprocess"] == "skipped"
        assert result["total_seconds"] >= 0

    def test_debugger_profile_plugin(self, tmp_path: Path):
        plugin_file = tmp_path / "profile_plugin.py"
        plugin_file.write_text(
            "from vector_studio.plugin_interface import Plugin\n"
            "class ProfilePlugin(Plugin):\n"
            "    name = 'profile'\n"
            "    version = '1.0.0'\n"
            "    description = 'profile'\n"
            "    def postprocess(self, svg_path, options):\n"
            "        return svg_path\n"
        )
        result = PluginDebugger.profile_plugin(plugin_file)
        assert "hook_times" in result
        assert result["hook_times"]["postprocess"] >= 0
        assert result["peak_memory_kb"] >= 0
        assert result["errors"] == []

    def test_debugger_test_plugin_failure(self, tmp_path: Path):
        plugin_file = tmp_path / "fail_plugin.py"
        plugin_file.write_text(
            "from vector_studio.plugin_interface import Plugin\n"
            "class FailPlugin(Plugin):\n"
            "    name = 'fail'\n"
            "    version = '1.0.0'\n"
            "    description = 'fail'\n"
            "    def preprocess(self, image, options):\n"
            "        raise RuntimeError('boom')\n"
        )
        result = PluginDebugger.test_plugin(plugin_file)
        assert result["passed"] is False
        assert any("boom" in e for e in result["errors"])


class TestPluginScaffold:
    def test_scaffold_generate(self, tmp_path: Path):
        path = PluginScaffold.generate("my-plugin", tmp_path, hooks=["preprocess", "postprocess"])
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "class MyPluginPlugin" in content
        assert "name = \"my-plugin\"" in content
        assert "def preprocess" in content
        assert "def postprocess" in content
        test_file = tmp_path / "test_my_plugin_plugin.py"
        assert test_file.exists()

    def test_scaffold_generate_from_template(self, tmp_path: Path):
        path = PluginScaffold.generate_from_template("watermark", "wm", tmp_path)
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "class WmPlugin" in content
        assert "name = \"wm\"" in content
        assert "postprocess" in content

    def test_scaffold_unknown_template_raises(self, tmp_path: Path):
        with pytest.raises(ValueError, match="Unknown template"):
            PluginScaffold.generate_from_template("nonexistent", "x", tmp_path)


class TestPluginDocsGenerator:
    def test_generate_readme(self, tmp_path: Path):
        plugin_file = tmp_path / "doc_plugin.py"
        plugin_file.write_text(
            "from vector_studio.plugin_interface import Plugin\n"
            "class DocPlugin(Plugin):\n"
            "    name = 'doc'\n"
            "    version = '2.0.0'\n"
            "    description = 'A doc plugin'\n"
            "    author = 'Tester'\n"
            "    def preprocess(self, image, options):\n"
            "        '''Rotate image.'''\n"
            "        return image\n"
        )
        readme = PluginDocsGenerator.generate_readme(plugin_file)
        assert "# doc" in readme
        assert "2.0.0" in readme
        assert "Tester" in readme
        assert "preprocess" in readme
        assert "vector-studio trace" in readme

    def test_generate_api_docs(self, tmp_path: Path):
        plugin_file = tmp_path / "api_plugin.py"
        plugin_file.write_text(
            "from vector_studio.plugin_interface import Plugin\n"
            "class ApiPlugin(Plugin):\n"
            "    name = 'api'\n"
            "    version = '1.0.0'\n"
            "    description = 'API plugin'\n"
            "    def postprocess(self, svg_path, options):\n"
            "        '''Clean SVG.'''\n"
            "        return svg_path\n"
        )
        docs = PluginDocsGenerator.generate_api_docs(tmp_path)
        assert "# Plugin API Documentation" in docs
        assert "api" in docs
        assert "postprocess" in docs
        assert "Clean SVG" in docs


class TestPluginSDK:
    def test_sdk_scaffold_creates_files(self, tmp_path: Path):
        sdk = PluginSDK(output_dir=tmp_path)
        plugin_dir = sdk.scaffold("My Plugin", "Author Name", "A test plugin", version="1.2.0")
        assert plugin_dir.exists()
        assert plugin_dir.is_dir()

        main_file = plugin_dir / "my_plugin.py"
        assert main_file.exists()
        content = main_file.read_text(encoding="utf-8")
        assert "class MyPlugin" in content
        assert 'name = \"my_plugin\"' in content
        assert 'version = \"1.2.0\"' in content
        assert "Author Name" in content
        assert "A test plugin" in content

        test_file = plugin_dir / "test_my_plugin.py"
        assert test_file.exists()

        readme = plugin_dir / "README.md"
        assert readme.exists()
        assert "My Plugin Plugin" in readme.read_text(encoding="utf-8")

        manifest = plugin_dir / "manifest.json"
        assert manifest.exists()
        assert "my_plugin" in manifest.read_text(encoding="utf-8")

    def test_sdk_validate_valid_plugin(self, tmp_path: Path):
        sdk = PluginSDK(output_dir=tmp_path)
        plugin_dir = sdk.scaffold("Valid", "A", "Desc")
        main_file = plugin_dir / "valid.py"
        result = sdk.validate(main_file)
        assert result["valid"] is True
        assert result["errors"] == []
        assert result["warnings"] == []  # manifest exists in scaffold

    def test_sdk_validate_missing_manifest_warning(self, tmp_path: Path):
        sdk = PluginSDK(output_dir=tmp_path)
        plugin_file = tmp_path / "lonely.py"
        plugin_file.write_text(
            "from vector_studio.plugin_interface import Plugin\n"
            "class Lonely(Plugin):\n"
            "    name = 'lonely'\n"
            "    version = '1.0.0'\n"
            "    description = 'lonely'\n"
        )
        result = sdk.validate(plugin_file)
        assert result["valid"] is True
        assert "缺少 manifest.json" in result["warnings"]

    def test_sdk_validate_nonexistent_file(self, tmp_path: Path):
        sdk = PluginSDK(output_dir=tmp_path)
        result = sdk.validate(tmp_path / "does_not_exist.py")
        assert result["valid"] is False
        assert "文件不存在" in result["errors"]

    def test_sdk_validate_missing_class(self, tmp_path: Path):
        sdk = PluginSDK(output_dir=tmp_path)
        bad = tmp_path / "bad.py"
        bad.write_text("# no definition here")
        result = sdk.validate(bad)
        assert result["valid"] is False
        assert any("未找到类定义" in e for e in result["errors"])

    def test_sdk_validate_missing_plugin_base(self, tmp_path: Path):
        sdk = PluginSDK(output_dir=tmp_path)
        bad = tmp_path / "bad.py"
        bad.write_text("class Foo:\n    pass")
        result = sdk.validate(bad)
        assert result["valid"] is False
        assert any("未继承 Plugin 基类" in e for e in result["errors"])
