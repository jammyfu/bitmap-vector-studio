from __future__ import annotations

import json
import os
import threading
import time
import uuid
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .batch_template import BatchTemplateApplier
from .cache_manager import CacheManager
from .checkpoint import CheckpointManager
from .cloud_market import (
    CloudMarket,
    CreditSystem,
    load_auth,
    save_auth,
)
from .cloud_storage import LocalStorage, StorageConfig, StorageManager
from .batch_rules import Rule, RuleEngine
from .config import Config
from .enterprise import (
    RolePermissions,
    SSOIntegration,
    TeamWorkspace,
)
from .external_editors import open_with_default_editor, open_with_editor
from .ocr_languages import (
    OCR_LANGUAGE_CONFIG,
    check_language_available,
    get_tesseract_languages,
    normalize_language_code,
    suggest_language_pack,
)
from .param_search import ParamGrid, quick_search, search_best_params
from .plugin_interface import Plugin
from .plugin_sdk import (
    PluginDebugger,
    PluginDocsGenerator,
    PluginScaffold,
    PluginSDK,
    PluginValidator,
)
from .plugin_market import PluginMarket
from .api_docs import APIDocsGenerator
from .community_tools import (
    ContributionGuideGenerator,
    PresetValidator,
)
from .plugins import PluginManager
from .presets import PRESETS, options_from_preset
from .report_generator import BatchReport, ConversionReport, ReportGenerator
from .stats_dashboard import StatsDashboard
from .svg_optimizer import svg_quality_score
from .svg_tools import svg_stats
from .design_integration import FigmaPlugin, SketchPlugin, DesignTokenSync
from .svg_3d import ARPreview, SVG3D
from .sync_service import SyncClient
from .task_queue import TaskQueue
from .template_market import Template, TemplateEditor, TemplateMarket
from .tracer import SUPPORTED_EXTENSIONS, trace_image
from .workflow import Workflow, WorkflowTemplate
from .workspace import Workspace, WorkspaceManager

from .notifier import Notifier
from .search_engine import HistorySearch, SearchEngine
from .security import InputValidator, SVGSanitizer, FileHashChecker, SecurityError
from .audit_logger import AuditLogger
from .migration import MigrationManager

from .animation import (
    AnimationBuilder,
    LottieExporter,
    SVGAnimation,
    list_presets as list_animation_presets,
)

from .i18n import t

console = Console()
app = typer.Typer(
    help="Bitmap Vector Studio v3.0.0 — 位图转矢量工具",
    no_args_is_help=True,
)

# Sub-typer for account commands
account_app = typer.Typer(help="Cloud account management.", hidden=True)
app.add_typer(account_app, name="account")

# Sub-typer for queue commands
queue_app = typer.Typer(help="Task queue management.", hidden=True)
app.add_typer(queue_app, name="queue")

# Sub-typer for config commands
config_app = typer.Typer(help="Configuration management.")
app.add_typer(config_app, name="config")

# Sub-typer for plugin commands
plugin_app = typer.Typer(help="Plugin management.")
app.add_typer(plugin_app, name="plugin")

# Sub-typer for plugin market commands
plugin_market_app = typer.Typer(help="Plugin marketplace.")
plugin_app.add_typer(plugin_market_app, name="market")

# Sub-typer for docs commands
docs_app = typer.Typer(help="Documentation generation.")
app.add_typer(docs_app, name="docs")

# Sub-typer for market commands
market_app = typer.Typer(help="Preset market management.")
app.add_typer(market_app, name="market")

# Sub-typer for workspace commands
workspace_app = typer.Typer(help="Workspace management.", hidden=True)
app.add_typer(workspace_app, name="workspace")

# Sub-typer for OCR commands
ocr_app = typer.Typer(help="OCR utilities.", hidden=True)
app.add_typer(ocr_app, name="ocr")

# Sub-typer for AI commands
ai_app = typer.Typer(help="Local ONNX AI processing.", hidden=True)
app.add_typer(ai_app, name="ai")

# Sub-typer for generate commands
generate_app = typer.Typer(help="AI generative vector creation.", hidden=True)
app.add_typer(generate_app, name="generate")

# Sub-typer for engine commands
engine_app = typer.Typer(help="Vectorization engine management.", hidden=True)
app.add_typer(engine_app, name="engine")

# Sub-typer for validate commands
validate_app = typer.Typer(help="Validation utilities.", hidden=True)
app.add_typer(validate_app, name="validate")

# Sub-typer for contrib commands
contrib_app = typer.Typer(help="Community contributor tools.", hidden=True)
app.add_typer(contrib_app, name="contrib")

# Sub-typer for cloud sync commands
cloud_app = typer.Typer(help="Cloud sync and sharing.", hidden=True)
app.add_typer(cloud_app, name="cloud")

# Sub-typer for cloud storage commands (under cloud)
storage_app = typer.Typer(help="Cloud storage management.")
cloud_app.add_typer(storage_app, name="storage")

# Sub-typer for rule commands
rule_app = typer.Typer(help="Batch rule engine management.")
app.add_typer(rule_app, name="rule")

# Sub-typer for animation commands
animate_app = typer.Typer(help="Vector animation export.", hidden=True)
app.add_typer(animate_app, name="animate")

# Sub-typer for design commands
design_app = typer.Typer(help="Design system integration.", hidden=True)
app.add_typer(design_app, name="design")

# Sub-typer for 3d commands
three_d_app = typer.Typer(help="3D vector effects and AR preview.", hidden=True)
app.add_typer(three_d_app, name="3d")

# Sub-typer for collaboration commands
collab_app = typer.Typer(help="Real-time collaboration rooms.", hidden=True)
app.add_typer(collab_app, name="collab")

# Sub-typer for workflow commands
workflow_app = typer.Typer(help="Visual workflow management.", hidden=True)
app.add_typer(workflow_app, name="workflow")

# Sub-typer for sync commands
sync_app = typer.Typer(help="Cross-device sync.", hidden=True)
app.add_typer(sync_app, name="sync")

# Sub-typer for render-farm commands
farm_app = typer.Typer(help="Distributed render farm.", hidden=True)
app.add_typer(farm_app, name="render-farm")

# Sub-typer for enterprise commands
enterprise_app = typer.Typer(help="Enterprise team and SSO management.", hidden=True)
app.add_typer(enterprise_app, name="enterprise")

# Sub-typer for template market commands
template_app = typer.Typer(help="Smart template marketplace.", hidden=True)
app.add_typer(template_app, name="template")

# Sub-typer for cache commands
cache_app = typer.Typer(help="Cache management.", hidden=True)
app.add_typer(cache_app, name="cache")

# Sub-typer for report commands
report_app = typer.Typer(help="Report generation and management.")
app.add_typer(report_app, name="report")

# Sub-typer for security commands
security_app = typer.Typer(help="Security and input validation utilities.")
app.add_typer(security_app, name="security")

# Sub-typer for audit commands
audit_app = typer.Typer(help="Audit log management.")
app.add_typer(audit_app, name="audit")

# Sub-typer for notify commands
notify_app = typer.Typer(help="Notification management.")
app.add_typer(notify_app, name="notify")

# Sub-typer for search commands
search_app = typer.Typer(help="Search history and files.")
app.add_typer(search_app, name="search")

# Conditional import so tests can patch vector_studio.cli.uvicorn.run
try:
    import uvicorn
except ImportError:  # pragma: no cover
    uvicorn = None  # type: ignore[assignment]


def _print_full_help() -> None:
    """Print comprehensive help including advanced commands."""
    console.print("\n[bold]Bitmap Vector Studio v3.0.0[/bold] — 位图转矢量工具\n")

    console.print("[bold cyan]核心命令:[/bold cyan]")
    console.print("  convert    转换图片为矢量格式 [默认]")
    console.print("  quick      一键转换（智能默认）")
    console.print("  config     配置管理")
    console.print("  plugin     插件管理")
    console.print("  market     预设/模板市场")
    console.print("  help       显示帮助信息")

    console.print("\n[bold cyan]高级命令:[/bold cyan]")
    console.print("  trace      单图转换 (已弃用，请使用 convert)")
    console.print("  batch      批量转换 (已弃用，请使用 convert --batch)")
    console.print("  benchmark  性能基准测试")
    console.print("  search     参数搜索")
    console.print("  resume     恢复中断的批量转换")
    console.print("  presets    列出内置预设")
    console.print("  api        启动API服务器")
    console.print("  account    云账户管理")
    console.print("  queue      任务队列管理")
    console.print("  workspace  工作区管理")
    console.print("  ocr        OCR工具")
    console.print("  ai         本地ONNX AI处理")
    console.print("  generate   AI生成矢量图")
    console.print("  engine     矢量化引擎管理")
    console.print("  validate   验证工具")
    console.print("  contrib    社区贡献工具")
    console.print("  cloud      云同步和分享")
    console.print("  animate    矢量动画导出")
    console.print("  design     设计系统集成")
    console.print("  3d         3D矢量效果和AR预览")
    console.print("  collab     实时协作房间")
    console.print("  workflow   可视工作流管理")
    console.print("  sync       跨设备同步")
    console.print("  render-farm 分布式渲染农场")
    console.print("  enterprise 企业团队和SSO管理")
    console.print("  template   智能模板市场")
    console.print("  cache      缓存管理")
    console.print("  report     报告生成与管理")
    console.print("  stats      统计仪表盘")

    console.print("\n[bold cyan]常用选项:[/bold cyan]")
    console.print("  --version   显示版本")
    console.print("  --help-all  显示所有命令（含高级）")
    console.print("  --quiet     静默输出")
    console.print("  --verbose   详细输出")

    console.print("\n[bold cyan]快速开始:[/bold cyan]")
    console.print("  vector-studio quick input.png           一键转换")
    console.print("  vector-studio convert input.png -p logo 使用预设转换")
    console.print("  vector-studio convert input.png -f pdf  导出PDF")
    console.print("  vector-studio report convert input.png  生成转换报告")
    console.print("  vector-studio stats                     显示统计仪表盘")

    console.print("\n[dim]文档: https://github.com/jammyfu/bitmap-vector-studio[/dim]\n")


@app.command("api", hidden=True)
def api_command(
    host: str = typer.Option("0.0.0.0", "--host", help="Bind host."),
    port: int = typer.Option(8000, "--port", help="Bind port."),
    workers: int = typer.Option(1, "--workers", help="Number of worker processes."),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for development."),
) -> None:
    """Start the Bitmap Vector Studio API server."""
    if uvicorn is None:
        console.print("[red]API dependencies are missing.[/red] Install with: pip install 'bitmap-vector-studio[api]'")
        raise typer.Exit(code=1)

    console.print(f"[green]Starting API server at[/green] http://{host}:{port}")
    uvicorn.run("vector_studio.api:app", host=host, port=port, workers=workers, reload=reload)


@app.callback(invoke_without_command=True)
def main_callback(
    api: bool = typer.Option(False, "--api", help="Start the API server instead of the CLI."),
    host: str = typer.Option("0.0.0.0", "--host"),
    port: int = typer.Option(8000, "--port"),
    reload: bool = typer.Option(False, "--reload"),
    help_all: bool = typer.Option(False, "--help-all", help="Show all commands including advanced ones."),
    version: bool = typer.Option(False, "--version", help="Show version."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Global quiet mode."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Global verbose mode."),
) -> None:
    """Global callback that intercepts --api, --help-all, and --version before any sub-command runs."""
    if help_all:
        _print_full_help()
        raise typer.Exit()
    if version:
        console.print(f"Bitmap Vector Studio v{__version__}")
        raise typer.Exit()
    if api:
        if uvicorn is None:
            console.print("[red]API dependencies are missing.[/red] Install with: pip install 'bitmap-vector-studio[api]'")
            raise typer.Exit(code=1)
        console.print(f"[green]Starting API server at[/green] http://{host}:{port}")
        uvicorn.run("vector_studio.api:app", host=host, port=port, workers=1, reload=reload)
        raise typer.Exit()


def _option_overrides(**kwargs):
    return {key: value for key, value in kwargs.items() if value is not None}


def _load_config(config_path: Path | None) -> Config:
    """Load configuration from an explicit path or the default location."""
    if config_path is not None:
        return Config.load(config_path)
    return Config.load()


def _active_plugins(config: Config, cli_plugins: list[str]) -> list[Plugin]:
    """Build the list of plugin instances to pass to ``trace_image``.

    Parameters
    ----------
    config:
        Loaded configuration.
    cli_plugins:
        Plugin names explicitly requested via ``--plugin``.

    Returns
    -------
    list[Plugin]
        Enabled plugin instances.
    """
    manager = PluginManager()
    manager.discover_plugins()

    # Apply config enabled_plugins
    for name in config.enabled_plugins:
        if name in manager._plugin_classes:
            manager.enable_plugin(name)
        else:
            # Silently ignore unknown plugins from config
            pass

    # Apply CLI overrides (explicit --plugin always wins)
    for name in cli_plugins:
        if name in manager._plugin_classes:
            manager.enable_plugin(name)
        else:
            console.print(f"[yellow]Warning:[/yellow] Unknown plugin '{name}'")

    return manager.get_plugins()


# ------------------------------------------------------------------
# Output helpers for "Less is More" CLI experience
# ------------------------------------------------------------------

def _print_analysis(input_path: Path, preset_name: str, confidence: float, features: dict[str, Any], quiet: bool, verbose: bool) -> None:
    if quiet:
        return
    if verbose:
        console.print(f"[分析] 图片: {input_path.name} ({features.get('width', '?')}x{features.get('height', '?')}, {features.get('color_count', '?')}色, 边缘密度: {features.get('edge_density', 0):.2f})")
        console.print(f"[推荐] {t('convert.recommending', preset=preset_name, confidence=round(confidence*100))}")
    else:
        console.print(f"{t('convert.analyzing')} ✓")
        console.print(t('convert.recommending', preset=preset_name, confidence=round(confidence*100)))


def _print_convert_progress(step: str, quiet: bool, verbose: bool) -> None:
    if quiet:
        return
    if verbose:
        console.print(f"[转换] {step}")
    else:
        console.print(f"{step}...", end=" ")


def _print_convert_done(quiet: bool, verbose: bool) -> None:
    if quiet:
        return
    if not verbose:
        console.print("✓")


def _print_result(result: Any, quiet: bool, verbose: bool, score: bool = False) -> None:
    if quiet:
        console.print(str(result.svg_path))
        return
    size_kb = result.svg_path.stat().st_size / 1024
    if verbose:
        console.print(f"[完成] 输出: {result.svg_path} ({size_kb:.1f}KB)")
        console.print(f"[引擎] {result.engine} | 时间: {result.elapsed_seconds:.2f}s")
        console.print(f"[统计] {result.stats}")
        if score:
            try:
                qs = svg_quality_score(result.svg_path)
                console.print(f"[质量] 评分: {qs['overall']}/100")
            except Exception as exc:
                console.print(f"[red]评分失败:[/red] {exc}")
    else:
        console.print(f"{t('convert.success', path=result.svg_path)} ({size_kb:.1f}KB)")


def _run_single_convert(
    input_path: Path,
    output: Path | None,
    preset: str | None,
    format: str,
    optimize_level: str,
    quiet: bool,
    verbose: bool,
    config_path: Path | None = None,
    plugin: list[str] | None = None,
    **kwargs: Any,
) -> Any:
    """Run a single-file conversion with smart preset recommendation."""
    config = _load_config(config_path)
    plugins = _active_plugins(config, plugin or [])

    # Auto-recommend preset if not specified
    if preset is None:
        from .smart_recommend import recommend_for_image
        preset_name, confidence, reason, features = recommend_for_image(input_path)
        _print_analysis(input_path, preset_name, confidence, features, quiet, verbose)
        preset = preset_name
    else:
        if not quiet:
            if verbose:
                console.print(f"[参数] 使用预设: {preset}")
            else:
                console.print(f"使用预设: {preset}")

    overrides = _option_overrides(**kwargs)
    opts = options_from_preset(preset, overrides)
    out = output or input_path.with_suffix(f".{format}")

    _print_convert_progress("转换", quiet, verbose)
    result = trace_image(
        input_path,
        out,
        opts,
        optimize_level=optimize_level,
        plugins=plugins,
    )
    _print_convert_done(quiet, verbose)
    _print_result(result, quiet, verbose)
    return result


# ------------------------------------------------------------------
# Convert app (unified conversion entry point)
# ------------------------------------------------------------------

convert_app = typer.Typer(help="转换图片为矢量格式（统一入口）")


@convert_app.command("file")
def convert_file(
    input_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="输入位图图片。"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="输出路径。"),
    preset: Optional[str] = typer.Option(None, "--preset", "-p", help="预设名称，不指定则自动推荐。"),
    format: str = typer.Option("svg", "--format", "-f", help="输出格式: svg/pdf/png/eps。"),
    optimize: str = typer.Option("basic", "--optimize", help="优化级别: none/basic/comprehensive/aggressive。"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="静默模式。"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="详细输出。"),
    config_path: Optional[Path] = typer.Option(None, "--config", help="配置文件路径。"),
    plugin: list[str] = typer.Option([], "--plugin", help="启用的插件名称（可多次使用）。"),
) -> None:
    """转换单张图片为矢量格式。"""
    _run_single_convert(
        input_path=input_path,
        output=output,
        preset=preset,
        format=format,
        optimize_level=optimize,
        quiet=quiet,
        verbose=verbose,
        config_path=config_path,
        plugin=plugin,
    )


@convert_app.command("batch")
def convert_batch(
    input_dir: Path = typer.Argument(..., exists=True, file_okay=False, readable=True, help="输入文件夹。"),
    output_dir: Path = typer.Argument(..., help="输出文件夹。"),
    preset: str = typer.Option("poster", "--preset", "-p", help="预设名称。"),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="递归扫描输入文件夹。"),
    overwrite: bool = typer.Option(False, "--overwrite", help="覆盖现有文件。"),
    optimize: str = typer.Option("basic", "--optimize", help="优化级别。"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="静默模式。"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="详细输出。"),
    workers: int = typer.Option(1, "--workers", "-w", min=1, max=16, help="并发工作数。"),
    config_path: Optional[Path] = typer.Option(None, "--config", help="配置文件路径。"),
    plugin: list[str] = typer.Option([], "--plugin", help="启用的插件名称。"),
) -> None:
    """批量转换文件夹中的图片。"""
    config = _load_config(config_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    opts = options_from_preset(preset)
    iterator = input_dir.rglob("*") if recursive else input_dir.glob("*")
    images = [path for path in iterator if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS]

    if not images:
        if not quiet:
            console.print(f"[yellow]{t('no_images')}[/yellow]")
        raise typer.Exit(code=0)

    plugins = _active_plugins(config, plugin)

    if not quiet:
        if verbose:
            console.print(f"[批量] 发现 {len(images)} 张图片，使用 {workers} 个工作线程")
        else:
            console.print(f"批量转换: {len(images)} 张图片")

    failures = 0
    for idx, image_path in enumerate(images, start=1):
        rel = image_path.relative_to(input_dir) if recursive else Path(image_path.name)
        out_path = (output_dir / rel).with_suffix(".svg")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if out_path.exists() and not overwrite:
            if verbose:
                console.print(f"[跳过] {out_path} (已存在)")
            continue
        try:
            if not quiet and not verbose:
                console.print(t('batch.progress', current=idx, total=len(images), filename=image_path.name, status=''), end=" ")
            result = trace_image(
                image_path,
                out_path,
                opts,
                optimize_level=optimize,
                plugins=plugins,
            )
            if not quiet:
                if verbose:
                    console.print(f"[完成] {result.svg_path}")
                else:
                    console.print("✓")
        except Exception as exc:
            failures += 1
            if not quiet:
                if verbose:
                    console.print(f"[失败] {image_path}: {exc}")
                else:
                    console.print(f"✗ ({exc})")

    if failures:
        if not quiet:
            console.print(f"[red]{t('batch.failures', failures=failures, total=len(images))}[/red]")
        raise typer.Exit(code=1)
    if not quiet:
        console.print(f"[green]{t('batch.summary', total=len(images))}[/green]")


@convert_app.command("generate")
def convert_generate(
    prompt: str = typer.Argument(..., help="AI 生成提示词。"),
    input_path: Optional[Path] = typer.Option(None, "--input", "-i", exists=True, dir_okay=False, readable=True, help="参考图片（可选）。"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="输出路径。"),
    style: str = typer.Option("flat", "--style", "-s", help="风格: flat, line, gradient, 3d, sketch。"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="静默模式。"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="详细输出。"),
) -> None:
    """使用 AI 生成矢量风格图片。"""
    from vector_studio.ai_generation import VectorGenerator
    from PIL import Image

    generator = VectorGenerator()
    if input_path is not None:
        with Image.open(input_path) as img:
            img = generator.generate_from_image(img, prompt=prompt)
    else:
        img = generator.generate_from_text(prompt, style=style)

    out = output or Path(f"generated_{style}.png")
    if out.suffix.lower() != ".png":
        out = out.with_suffix(".png")
    img.save(out, format="PNG", optimize=True)

    if not quiet:
        if verbose:
            console.print(f"[生成] 已保存 {out} ({img.size[0]}x{img.size[1]})")
        else:
            console.print(f"生成完成 → {out} ({img.size[0]}x{img.size[1]})")
    else:
        console.print(str(out))


app.add_typer(convert_app, name="convert")


@app.command("quick")
def quick_command(
    input_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="输入位图图片。"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="输出路径。"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="静默模式。"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="详细输出。"),
) -> None:
    """一键转换：自动推荐最佳预设并转换。"""
    _run_single_convert(
        input_path=input_path,
        output=output,
        preset=None,
        format="svg",
        optimize_level="basic",
        quiet=quiet,
        verbose=verbose,
    )


@app.command("presets", hidden=True)
def list_presets() -> None:
    """Show available presets and their core settings."""
    table = Table(title="Built-in presets")
    table.add_column("Name", style="bold")
    table.add_column("Color")
    table.add_column("Hierarchy")
    table.add_column("Curve")
    table.add_column("Color precision")
    table.add_column("Layer diff")
    table.add_column("Speckle")

    for name, opts in PRESETS.items():
        table.add_row(
            name,
            opts.colormode,
            opts.hierarchical,
            opts.mode,
            str(opts.color_precision),
            str(opts.layer_difference),
            str(opts.filter_speckle),
        )
    console.print(table)


@app.command("trace", hidden=True)
def trace_command(
    input_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Input bitmap image."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output SVG path."),
    preset: str = typer.Option("poster", "--preset", "-p", help="Preset: bw, poster, photo, logo, pixel_art, scan, custom."),
    colormode: Optional[str] = typer.Option(None, "--colormode", help="color or binary."),
    hierarchical: Optional[str] = typer.Option(None, "--hierarchical", help="stacked or cutout."),
    mode: Optional[str] = typer.Option(None, "--mode", help="spline, polygon, pixel, or none."),
    filter_speckle: Optional[int] = typer.Option(None, "--filter-speckle", min=0, max=128),
    color_precision: Optional[int] = typer.Option(None, "--color-precision", min=1, max=8),
    layer_difference: Optional[int] = typer.Option(None, "--layer-difference", min=0, max=255),
    corner_threshold: Optional[int] = typer.Option(None, "--corner-threshold", min=0, max=180),
    length_threshold: Optional[float] = typer.Option(None, "--length-threshold", min=3.5, max=10.0),
    max_iterations: Optional[int] = typer.Option(None, "--max-iterations", min=1, max=50),
    splice_threshold: Optional[int] = typer.Option(None, "--splice-threshold", min=0, max=180),
    path_precision: Optional[int] = typer.Option(None, "--path-precision", min=0, max=12),
    denoise: Optional[bool] = typer.Option(None, "--denoise/--no-denoise"),
    posterize: Optional[int] = typer.Option(None, "--posterize", min=1, max=8, help="Optional Pillow posterize bits."),
    max_input_side: Optional[int] = typer.Option(None, "--max-input-side", min=64, help="Downscale max side before tracing."),
    optimize: bool = typer.Option(True, "--optimize/--no-optimize", help="Conservative SVG cleanup."),
    optimize_level: str = typer.Option("basic", "--optimize-level", help="none, basic, comprehensive, aggressive."),
    score: bool = typer.Option(False, "--score", help="Output quality score after conversion."),
    name_layers: bool = typer.Option(False, "--name-layers", help="Add meaningful layer names to the output SVG."),
    export_pdf: bool = typer.Option(False, "--export-pdf", help="Also export PDF via CairoSVG."),
    export_png: bool = typer.Option(False, "--export-png", help="Also export PNG preview via CairoSVG."),
    export_eps: bool = typer.Option(False, "--export-eps", help="Also export EPS via Inkscape CLI."),
    open_editor: Optional[str] = typer.Option(None, "--open", help="Open the output SVG in an external editor (inkscape, illustrator, etc.). Use without value for default editor."),
    smart_remove_bg: bool = typer.Option(False, "--smart-remove-bg", help="Auto-detect and remove background for logo-like images."),
    enhance: Optional[str] = typer.Option(None, "--enhance", help="Enhancement type: scan, photo, logo, auto."),
    ai_simplify: bool = typer.Option(False, "--ai-simplify", help="Apply AI semantic simplification before tracing."),
    ai_ocr: bool = typer.Option(False, "--ai-ocr", help="Detect and embed text as editable SVG text elements."),
    ocr_lang: Optional[str] = typer.Option(None, "--ocr-lang", help="OCR language code (e.g. chi_sim, jpn, kor, ara, rus, deu, fra, spa)."),
    ocr_vertical: bool = typer.Option(False, "--ocr-vertical", help="Detect vertical text orientation during OCR."),
    simplify_type: str = typer.Option("auto", "--simplify-type", help="Simplification strategy: photo, complex, sketch, auto."),
    recommend: bool = typer.Option(False, "--recommend", help="Only analyze and recommend a preset, do not convert."),
    region: Optional[str] = typer.Option(None, "--region", help="Rectangular region to trace as x,y,w,h."),
    live_preview: bool = typer.Option(False, "--live-preview", help="Fast low-res preview mode."),
    config_path: Optional[Path] = typer.Option(None, "--config", help="Path to configuration file."),
    plugin: list[str] = typer.Option([], "--plugin", help="Enable a plugin by name (can be used multiple times)."),
    gpu: bool = typer.Option(False, "--gpu", help="Use GPU-accelerated preprocessing if available."),
    stream: bool = typer.Option(False, "--stream", help="Force chunked/streaming processing for large images."),
    engine: str = typer.Option("vtracer", "--engine", "-e", help="Vectorization engine: vtracer, potrace, autotrace."),
    ai_pipeline: list[str] = typer.Option([], "--ai-pipeline", help="AI pre-processing tasks: segment, style_transfer, upscale, auto_enhance."),
) -> None:
    """Convert one bitmap image to SVG. (Deprecated: use 'convert' instead)"""
    console.print(f"[yellow]{t('deprecated.trace')}[/yellow]")
    config = _load_config(config_path)

    # Apply config defaults when the CLI value matches the hardcoded default
    # and the config provides a different value.
    if config.default_preset and preset == "poster":
        preset = config.default_preset
    if config.default_optimize_level and optimize_level == "basic":
        optimize_level = config.default_optimize_level
    if not smart_remove_bg and config.smart_remove_bg:
        smart_remove_bg = config.smart_remove_bg
    if enhance is None and config.enhance is not None:
        enhance = config.enhance
    if not export_pdf and config.export_pdf:
        export_pdf = config.export_pdf
    if not export_png and config.export_png:
        export_png = config.export_png

    if recommend:
        from .smart_recommend import recommend_for_image
        preset_name, confidence, reason, features = recommend_for_image(input_path)
        table = Table(title="Smart Preset Recommendation")
        table.add_column("Property", style="bold")
        table.add_column("Value")
        table.add_row("Recommended preset", preset_name)
        table.add_row("Confidence", f"{confidence:.0%}")
        table.add_row("Reason", reason)
        table.add_row("Colors", str(features.get("color_count")))
        table.add_row("Edge density", f"{features.get('edge_density', 0):.3f}")
        table.add_row("Aspect ratio", str(features.get("aspect_ratio")))
        table.add_row("Likely logo", str(features.get("is_likely_logo")))
        console.print(table)
        return

    overrides = _option_overrides(
        colormode=colormode,
        hierarchical=hierarchical,
        mode=mode,
        filter_speckle=filter_speckle,
        color_precision=color_precision,
        layer_difference=layer_difference,
        corner_threshold=corner_threshold,
        length_threshold=length_threshold,
        max_iterations=max_iterations,
        splice_threshold=splice_threshold,
        path_precision=path_precision,
        denoise=denoise,
        posterize=posterize,
        max_input_side=max_input_side,
    )
    opts = options_from_preset(preset, overrides)
    out = output or input_path.with_suffix(".svg")

    plugins = _active_plugins(config, plugin)

    if live_preview:
        from .live_preview import LivePreviewEngine
        preview_engine = LivePreviewEngine(max_size=400)
        preview_path, elapsed = preview_engine.generate_preview(input_path, opts)
        if output and Path(preview_path).resolve() != Path(out).resolve():
            import shutil
            shutil.copy2(preview_path, out)
            console.print(f"[green]Preview[/green] {out}")
        else:
            console.print(f"[green]Preview[/green] {preview_path}")
        console.print(f"Time: {elapsed:.2f}s")
        return

    if region:
        from .region_trace import RegionSelector, region_trace
        parts = region.split(",")
        if len(parts) != 4:
            console.print("[red]Error:[/red] --region must be x,y,w,h")
            raise typer.Exit(code=1)
        try:
            x, y, w, h = (int(p.strip()) for p in parts)
        except ValueError:
            console.print("[red]Error:[/red] --region values must be integers")
            raise typer.Exit(code=1)
        region_sel = RegionSelector(x=x, y=y, width=w, height=h, shape="rect")
        result = region_trace(input_path, region_sel, out, opts)
        console.print(f"[green]Done[/green] {result.svg_path}")
        console.print(f"Engine: {result.engine} | Time: {result.elapsed_seconds:.2f}s")
        console.print(f"Stats: {result.stats}")
        return

    result = trace_image(
        input_path,
        out,
        opts,
        engine=engine,
        optimize=optimize,
        optimize_level=optimize_level,
        name_layers=name_layers,
        export_pdf=export_pdf,
        export_png=export_png,
        export_eps=export_eps,
        smart_remove_bg=smart_remove_bg,
        enhance=enhance,
        plugins=plugins,
        ai_simplify=ai_simplify,
        ai_ocr=ai_ocr,
        ocr_lang=ocr_lang,
        simplify_type=simplify_type,
        use_gpu=gpu,
        stream=stream,
        ai_pipeline=ai_pipeline if ai_pipeline else None,
    )

    console.print(f"[green]Done[/green] {result.svg_path}")
    console.print(f"Engine: {result.engine} | Time: {result.elapsed_seconds:.2f}s")
    console.print(f"Stats: {result.stats}")
    if score:
        try:
            qs = svg_quality_score(result.svg_path)
            console.print(f"Quality score: {qs['overall']}/100 (size={qs['file_size_score']}, paths={qs['path_efficiency']}, complexity={qs['complexity_score']}, colors={qs['color_efficiency']})")
        except Exception as exc:
            console.print(f"[red]Score failed:[/red] {exc}")
    if result.pdf_path:
        console.print(f"PDF: {result.pdf_path}")
    if result.png_path:
        console.print(f"PNG: {result.png_path}")
    if result.eps_path:
        console.print(f"EPS: {result.eps_path}")

    if open_editor is not None:
        try:
            if open_editor:
                open_with_editor(result.svg_path, open_editor)
            else:
                open_with_default_editor(result.svg_path)
            console.print(f"[cyan]Opened[/cyan] {result.svg_path} in editor")
        except Exception as exc:
            console.print(f"[red]Failed to open editor:[/red] {exc}")


@app.command("benchmark", hidden=True)
def benchmark_command(
    input_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Input bitmap image."),
    preset: str = typer.Option("poster", "--preset", "-p", help="Preset to use."),
    runs: int = typer.Option(3, "--runs", "-r", min=1, max=20, help="Number of benchmark runs."),
    gpu: bool = typer.Option(False, "--gpu", help="Use GPU-accelerated preprocessing if available."),
    stream: bool = typer.Option(False, "--stream", help="Force chunked/streaming processing."),
) -> None:
    """Run a performance benchmark on a single image."""
    from .performance import PerformanceMonitor
    from .startup_optimizer import StartupProfiler

    opts = options_from_preset(preset)
    monitor = PerformanceMonitor()

    # Estimate before running
    from PIL import Image

    with Image.open(input_path) as img:
        estimated = monitor.estimate_conversion_time(img.size, opts)
    console.print(f"[cyan]Estimated time:[/cyan] {estimated:.2f}s per run")

    times: list[float] = []
    with StartupProfiler(label="benchmark") as profiler:
        profiler.stage("warmup")
        # Warm-up run (not counted)
        trace_image(input_path, input_path.with_suffix(".svg"), opts, use_gpu=gpu, stream=stream)

        for i in range(runs):
            profiler.stage(f"run_{i + 1}")
            result = trace_image(input_path, input_path.with_suffix(".svg"), opts, use_gpu=gpu, stream=stream)
            times.append(result.elapsed_seconds)

    table = Table(title=f"Benchmark: {input_path.name} ({runs} runs)")
    table.add_column("Metric", style="bold")
    table.add_column("Value")
    table.add_row("Min", f"{min(times):.3f}s")
    table.add_row("Max", f"{max(times):.3f}s")
    table.add_row("Mean", f"{sum(times) / len(times):.3f}s")
    table.add_row("Median", f"{sorted(times)[len(times) // 2]:.3f}s")
    table.add_row("Engine", result.engine)
    console.print(table)

    report = profiler.get_report()
    console.print(f"[cyan]Bottleneck:[/cyan] {report['bottleneck']} ({report['total_seconds']:.3f}s total)")


@app.command("batch", hidden=True)
def batch_command(
    input_dir: Path = typer.Argument(..., exists=True, file_okay=False, readable=True, help="Input folder."),
    output_dir: Path = typer.Argument(..., help="Output folder."),
    preset: str = typer.Option("poster", "--preset", "-p"),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Scan input folder recursively."),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing SVG files."),
    name_layers: bool = typer.Option(False, "--name-layers", help="Add meaningful layer names to each output SVG."),
    optimize_level: str = typer.Option("basic", "--optimize-level", help="none, basic, comprehensive, aggressive."),
    score: bool = typer.Option(False, "--score", help="Output quality score after each conversion."),
    export_pdf: bool = typer.Option(False, "--export-pdf"),
    export_png: bool = typer.Option(False, "--export-png"),
    open_editor: bool = typer.Option(False, "--open", help="Open each output SVG in the default external editor after conversion."),
    workers: int = typer.Option(1, "--workers", "-w", min=1, max=16, help="Number of concurrent workers."),
    retry: int = typer.Option(0, "--retry", min=0, max=5, help="Number of retries on failure."),
    config_path: Optional[Path] = typer.Option(None, "--config", help="Path to configuration file."),
    plugin: list[str] = typer.Option([], "--plugin", help="Enable a plugin by name (can be used multiple times)."),
    checkpoint: bool = typer.Option(False, "--checkpoint", help="Enable checkpoint/resume for this batch."),
) -> None:
    """Batch-convert a folder of images. (Deprecated: use 'convert batch' instead)"""
    console.print(f"[yellow]{t('deprecated.batch')}[/yellow]")
    config = _load_config(config_path)

    if config.default_preset and preset == "poster":
        preset = config.default_preset
    if config.default_optimize_level and optimize_level == "basic":
        optimize_level = config.default_optimize_level
    if not export_pdf and config.export_pdf:
        export_pdf = config.export_pdf
    if not export_png and config.export_png:
        export_png = config.export_png

    output_dir.mkdir(parents=True, exist_ok=True)
    opts = options_from_preset(preset)
    iterator = input_dir.rglob("*") if recursive else input_dir.glob("*")
    images = [path for path in iterator if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS]

    if not images:
        console.print(f"[yellow]{t('no_images')}[/yellow]")
        raise typer.Exit(code=0)

    plugins = _active_plugins(config, plugin)

    # When workers == 1 and retry == 0, keep the original sequential behaviour.
    if workers == 1 and retry == 0:
        table = Table(title=f"Batch conversion: {len(images)} image(s)")
        table.add_column("Input")
        table.add_column("Output")
        table.add_column("Status")

        failures = 0
        for image_path in images:
            rel = image_path.relative_to(input_dir) if recursive else Path(image_path.name)
            out_path = (output_dir / rel).with_suffix(".svg")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            if out_path.exists() and not overwrite:
                table.add_row(str(image_path), str(out_path), "skipped")
                continue
            try:
                result = trace_image(
                    image_path,
                    out_path,
                    opts,
                    optimize_level=optimize_level,
                    export_pdf=export_pdf,
                    export_png=export_png,
                    name_layers=name_layers,
                    plugins=plugins,
                )
                table.add_row(str(image_path), str(result.svg_path), "ok")
                if score:
                    try:
                        qs = svg_quality_score(result.svg_path)
                        console.print(f"  Score {result.svg_path.name}: {qs['overall']}/100")
                    except Exception:
                        pass
                if open_editor:
                    try:
                        open_with_default_editor(result.svg_path)
                    except Exception as open_exc:
                        console.print(f"[red]Failed to open {result.svg_path}:[/red] {open_exc}")
            except Exception as exc:  # noqa: BLE001 - CLI should continue batch work.
                failures += 1
                table.add_row(str(image_path), str(out_path), f"failed: {exc}")

        console.print(table)
        if failures:
            raise typer.Exit(code=1)
        return

    # Concurrent path via TaskQueue.
    cp_mgr = CheckpointManager() if checkpoint else None
    q = TaskQueue(max_workers=workers, output_dir=output_dir, max_retries=retry, checkpoint_manager=cp_mgr)
    for image_path in images:
        rel = image_path.relative_to(input_dir) if recursive else Path(image_path.name)
        out_path = (output_dir / rel).with_suffix(".svg")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if out_path.exists() and not overwrite:
            console.print(f"[yellow]Skipped[/yellow] {out_path} (exists)")
            continue
        q.add_task(image_path, out_path, opts, optimize_level=optimize_level, plugins=plugins)

    q.start()
    results = q.wait_for_all()

    # Clean up checkpoint on successful completion.
    if checkpoint and cp_mgr is not None:
        cp_mgr.delete_checkpoint(q.queue_id)

    table = Table(title=f"Batch conversion: {len(results)} image(s)")
    table.add_column("Input")
    table.add_column("Output")
    table.add_column("Status")

    failures = 0
    for task in results:
        if task.status == "completed":
            table.add_row(str(task.input_path), str(task.output_path), "ok")
            if open_editor:
                try:
                    open_with_default_editor(task.output_path)
                except Exception as open_exc:
                    console.print(f"[red]Failed to open {task.output_path}:[/red] {open_exc}")
        elif task.status == "failed":
            failures += 1
            table.add_row(str(task.input_path), str(task.output_path), f"failed: {task.error}")
        else:
            table.add_row(str(task.input_path), str(task.output_path), task.status)

    console.print(table)
    if failures:
        raise typer.Exit(code=1)


@app.command("search", hidden=True)
def search_command(
    input_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Input bitmap image."),
    output_dir: Path = typer.Option(..., "--output-dir", "-o", help="Directory to store search results."),
    max_combinations: int = typer.Option(20, "--max", "-m", min=1, max=100, help="Maximum parameter combinations to try."),
    quick: bool = typer.Option(False, "--quick", help="Run a quick preset-only search instead of full grid search."),
) -> None:
    """Search for the best tracing parameters for a single image."""
    output_dir.mkdir(parents=True, exist_ok=True)

    if quick:
        best_preset, best_path, best_score = quick_search(input_path, output_dir)
        console.print(f"[green]Best preset:[/green] {best_preset} (score={best_score:.1f})")
        console.print(f"Output: {best_path}")
        stats = svg_stats(best_path)
        console.print(f"Stats: {stats}")
        return

    best_options, best_path, best_score, all_results = search_best_params(
        input_path, output_dir, max_combinations=max_combinations
    )

    console.print(f"[green]Best score:[/green] {best_score:.1f}")
    console.print(f"Output: {best_path}")
    console.print(f"Options: {best_options}")
    stats = svg_stats(best_path)
    console.print(f"Stats: {stats}")

    table = Table(title=f"Search results ({len(all_results)} combinations)")
    table.add_column("#")
    table.add_column("Preset")
    table.add_column("Color precision")
    table.add_column("Speckle")
    table.add_column("Layer diff")
    table.add_column("Corner")
    table.add_column("Score")
    table.add_column("Status")

    for idx, res in enumerate(all_results, start=1):
        opts = res["options"]
        status = "ok" if "error" not in res else f"error: {res['error']}"
        table.add_row(
            str(idx),
            opts.colormode,
            str(opts.color_precision),
            str(opts.filter_speckle),
            str(opts.layer_difference),
            str(opts.corner_threshold),
            f"{res['score']:.1f}",
            status,
        )
    console.print(table)


# ------------------------------------------------------------------
# Config sub-commands
# ------------------------------------------------------------------

@config_app.command("show")
def config_show(config_path: Optional[Path] = typer.Option(None, "--config", help="Path to configuration file.")) -> None:
    """Display the current configuration."""
    cfg = _load_config(config_path)
    table = Table(title="Bitmap Vector Studio Configuration")
    table.add_column("Key", style="bold")
    table.add_column("Value")
    for key, value in cfg.to_dict().items():
        table.add_row(key, str(value))
    console.print(table)
    errors = cfg.validate()
    if errors:
        for err in errors:
            console.print(f"[red]Validation error:[/red] {err}")
        raise typer.Exit(code=1)
    else:
        console.print("[green]Configuration is valid.[/green]")


@config_app.command("init")
def config_init(
    path: Optional[Path] = typer.Option(None, "--path", help="Destination path for the config file."),
    force: bool = typer.Option(False, "--force", help="Overwrite existing file."),
) -> None:
    """Generate a default configuration file."""
    from .config import _default_config_path
    dest = path or _default_config_path()
    if dest.exists() and not force:
        console.print(f"[yellow]Config file already exists:[/yellow] {dest}")
        console.print("Use --force to overwrite.")
        raise typer.Exit(code=1)
    cfg = Config()
    cfg.save(dest)
    console.print(f"[green]Created config file:[/green] {dest}")


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Configuration key to set."),
    value: str = typer.Argument(..., help="Value to assign."),
    path: Optional[Path] = typer.Option(None, "--path", help="Path to configuration file."),
) -> None:
    """Set a configuration value and save it."""
    cfg = Config.load(path)
    data = cfg.to_dict()

    if key not in data:
        console.print(f"[red]Unknown config key:[/red] {key}")
        console.print(f"Valid keys: {', '.join(sorted(data.keys()))}")
        raise typer.Exit(code=1)

    # Attempt type coercion based on the current value type.
    current = data[key]
    if isinstance(current, bool):
        parsed = value.lower() in {"true", "1", "yes", "on"}
    elif isinstance(current, int):
        try:
            parsed = int(value)
        except ValueError:
            console.print(f"[red]Invalid integer:[/red] {value}")
            raise typer.Exit(code=1)
    elif isinstance(current, list):
        # Split comma-separated strings into lists.
        parsed = [v.strip() for v in value.split(",") if v.strip()]
    else:
        parsed = value

    data[key] = parsed
    new_cfg = Config.from_dict(data)
    new_cfg.save(path)
    console.print(f"[green]Set[/green] {key} = {parsed}")


@config_app.command("validate")
def config_validate(
    path: Optional[Path] = typer.Option(None, "--path", help="Path to configuration file."),
) -> None:
    """Validate the configuration file."""
    cfg = Config.load(path)
    errors = cfg.validate()
    if errors:
        for err in errors:
            console.print(f"[red]Validation error:[/red] {err}")
        raise typer.Exit(code=1)
    console.print("[green]Configuration is valid.[/green]")


# ------------------------------------------------------------------
# Plugin sub-commands
# ------------------------------------------------------------------

@plugin_app.command("list")
def plugin_list() -> None:
    """List all discovered plugins."""
    manager = PluginManager()
    manager.discover_plugins()
    plugins = manager.list_plugins()

    if not plugins:
        console.print("[yellow]No plugins discovered.[/yellow]")
        return

    table = Table(title="Plugins")
    table.add_column("Name", style="bold")
    table.add_column("Version")
    table.add_column("Description")
    table.add_column("Author")
    table.add_column("Enabled")
    table.add_column("Hooks")

    for info in plugins:
        table.add_row(
            info["name"],
            info["version"],
            info["description"],
            info["author"],
            "yes" if info["enabled"] else "no",
            ", ".join(info["hooks"]) or "-",
        )
    console.print(table)


@plugin_app.command("enable")
def plugin_enable(name: str = typer.Argument(..., help="Plugin name to enable.")) -> None:
    """Enable a plugin in the user configuration."""
    manager = PluginManager()
    manager.discover_plugins()
    if name not in manager._plugin_classes:
        console.print(f"[red]Unknown plugin:[/red] {name}")
        raise typer.Exit(code=1)
    manager.enable_plugin(name)
    cfg = Config.load()
    if name not in cfg.enabled_plugins:
        cfg.enabled_plugins.append(name)
        cfg.save()
    console.print(f"[green]Enabled plugin:[/green] {name}")


@plugin_app.command("disable")
def plugin_disable(name: str = typer.Argument(..., help="Plugin name to disable.")) -> None:
    """Disable a plugin in the user configuration."""
    manager = PluginManager()
    manager.discover_plugins()
    if name not in manager._plugin_classes:
        console.print(f"[red]Unknown plugin:[/red] {name}")
        raise typer.Exit(code=1)
    manager.disable_plugin(name)
    cfg = Config.load()
    if name in cfg.enabled_plugins:
        cfg.enabled_plugins.remove(name)
        cfg.save()
    console.print(f"[green]Disabled plugin:[/green] {name}")


@plugin_app.command("install")
def plugin_install(
    source: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Path to the plugin .py file."),
) -> None:
    """Install a plugin into the user plugin directory."""
    manager = PluginManager()
    try:
        dest = manager.install_plugin(source)
    except Exception as exc:
        console.print(f"[red]Installation failed:[/red] {exc}")
        raise typer.Exit(code=1)
    console.print(f"[green]Installed plugin to:[/green] {dest}")


@plugin_app.command("validate")
def plugin_validate(
    path: Path = typer.Argument(..., exists=True, readable=True, help="Path to a plugin .py file or directory."),
) -> None:
    """Validate a plugin file or all plugins in a directory."""
    if path.is_dir():
        results = PluginValidator.validate_batch(path)
        table = Table(title=f"Plugin Validation: {path}")
        table.add_column("File", style="bold")
        table.add_column("Status")
        table.add_column("Errors")
        for res in results:
            status = "[green]ok[/green]" if res["passed"] else "[red]fail[/red]"
            errors = "; ".join(res["errors"]) if res["errors"] else "-"
            table.add_row(Path(res["path"]).name, status, errors)
        console.print(table)
        if any(not r["passed"] for r in results):
            raise typer.Exit(code=1)
    else:
        passed, errors = PluginValidator.validate(path)
        if passed:
            console.print(f"[green]Plugin is valid:[/green] {path}")
        else:
            console.print(f"[red]Plugin validation failed:[/red] {path}")
            for err in errors:
                console.print(f"  - {err}")
            raise typer.Exit(code=1)


@plugin_app.command("test")
def plugin_test(
    path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Path to a plugin .py file."),
) -> None:
    """Test a plugin in an isolated environment."""
    result = PluginDebugger.test_plugin(path)
    table = Table(title=f"Plugin Test: {path.name}")
    table.add_column("Hook", style="bold")
    table.add_column("Result")
    for hook, status in result["hook_results"].items():
        color = "green" if status == "ok" else ("yellow" if status == "skipped" else "red")
        table.add_row(hook, f"[{color}]{status}[/{color}]")
    console.print(table)
    if result["errors"]:
        for err in result["errors"]:
            console.print(f"[red]Error:[/red] {err}")
    console.print(f"Total time: {result['total_seconds']:.4f}s")
    if not result["passed"]:
        raise typer.Exit(code=1)


@plugin_app.command("scaffold")
def plugin_scaffold(
    name: str = typer.Argument(..., help="Name for the new plugin."),
    output_dir: Path = typer.Option(Path("."), "--output-dir", "-o", help="Directory to write the plugin."),
    template: str = typer.Option("", "--template", "-t", help="Built-in template: watermark, resize, filter, annotate."),
    hooks: str = typer.Option("", "--hooks", help="Comma-separated hooks: preprocess,postprocess,on_complete"),
) -> None:
    """Generate a new plugin scaffold."""
    output_dir.mkdir(parents=True, exist_ok=True)
    if template:
        try:
            path = PluginScaffold.generate_from_template(template, name, output_dir)
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=1)
    else:
        hook_list = [h.strip() for h in hooks.split(",") if h.strip()] or None
        path = PluginScaffold.generate(name, output_dir, hooks=hook_list)
    console.print(f"[green]Created plugin:[/green] {path}")
    test_file = path.with_name(f"test_{path.stem}.py")
    if test_file.exists():
        console.print(f"[green]Created test:[/green] {test_file}")


@plugin_app.command("docs")
def plugin_docs(
    path: Path = typer.Argument(..., exists=True, readable=True, help="Path to a plugin .py file or directory."),
    output: Path = typer.Option(None, "--output", "-o", help="Output markdown file."),
) -> None:
    """Generate documentation for a plugin or a directory of plugins."""
    if path.is_dir():
        md = PluginDocsGenerator.generate_api_docs(path)
    else:
        md = PluginDocsGenerator.generate_readme(path)
    if output:
        output.write_text(md, encoding="utf-8")
        console.print(f"[green]Saved docs to:[/green] {output}")
    else:
        console.print(md)


# ------------------------------------------------------------------
# Plugin market sub-commands
# ------------------------------------------------------------------

@plugin_market_app.command("list")
def plugin_market_list(
    category: str | None = typer.Option(None, "--category", "-c", help="Filter by category."),
    sort_by: str = typer.Option("rating", "--sort", "-s", help="Sort by: rating, downloads, name, newest."),
) -> None:
    """List available plugins from the marketplace."""
    market = PluginMarket()
    plugins = market.discover_plugins(category=category, sort_by=sort_by)
    if not plugins:
        console.print("[yellow]No plugins found in the market.[/yellow]")
        return

    table = Table(title="Plugin Market")
    table.add_column("ID", style="bold")
    table.add_column("Name")
    table.add_column("Category")
    table.add_column("Version")
    table.add_column("Rating")
    table.add_column("Downloads")
    table.add_column("Installed")

    for p in plugins:
        table.add_row(
            p.package_id,
            p.name,
            market.CATEGORIES.get(p.category, p.category),
            p.version,
            f"{p.rating:.1f}",
            str(p.downloads),
            "yes" if p.installed else "no",
        )
    console.print(table)


@plugin_market_app.command("search")
def plugin_market_search(
    query: str = typer.Argument(..., help="Search query."),
    category: str | None = typer.Option(None, "--category", "-c", help="Filter by category."),
    sort_by: str = typer.Option("rating", "--sort", "-s", help="Sort by: rating, downloads, name, newest."),
) -> None:
    """Search for plugins in the marketplace."""
    market = PluginMarket()
    plugins = market.discover_plugins(query=query, category=category, sort_by=sort_by)
    if not plugins:
        console.print(f"[yellow]No plugins found for '{query}'.[/yellow]")
        return

    table = Table(title=f"Plugin Search: {query}")
    table.add_column("ID", style="bold")
    table.add_column("Name")
    table.add_column("Category")
    table.add_column("Rating")
    table.add_column("Downloads")

    for p in plugins:
        table.add_row(
            p.package_id,
            p.name,
            market.CATEGORIES.get(p.category, p.category),
            f"{p.rating:.1f}",
            str(p.downloads),
        )
    console.print(table)


@plugin_market_app.command("install")
def plugin_market_install(
    package_id: str = typer.Argument(..., help="Plugin package ID to install."),
    source: Path = typer.Option(..., "--source", "-s", exists=True, dir_okay=False, readable=True, help="Path to the plugin .py file."),
) -> None:
    """Install a plugin from the marketplace."""
    market = PluginMarket()
    plugin = market.get_plugin(package_id)
    if plugin is None:
        console.print(f"[red]Unknown plugin:[/red] {package_id}")
        raise typer.Exit(code=1)

    try:
        market.install_plugin(package_id, source)
    except Exception as exc:
        console.print(f"[red]Installation failed:[/red] {exc}")
        raise typer.Exit(code=1)
    console.print(f"[green]Installed plugin:[/green] {package_id}")


@plugin_market_app.command("rate")
def plugin_market_rate(
    package_id: str = typer.Argument(..., help="Plugin package ID to rate."),
    stars: int = typer.Option(..., "--stars", min=1, max=5, help="Rating from 1 to 5."),
    user_id: str = typer.Option("cli_user", "--user", "-u", help="User identifier."),
) -> None:
    """Rate a plugin in the marketplace."""
    market = PluginMarket()
    plugin = market.get_plugin(package_id)
    if plugin is None:
        console.print(f"[red]Unknown plugin:[/red] {package_id}")
        raise typer.Exit(code=1)

    success = market.rate_plugin(package_id, user_id, stars)
    if success:
        console.print(f"[green]Rated[/green] {package_id} {stars} stars")
    else:
        console.print(f"[red]Rating failed:[/red] must be 1-5 stars")
        raise typer.Exit(code=1)


# ------------------------------------------------------------------
# Docs sub-commands
# ------------------------------------------------------------------

@docs_app.command("generate")
def docs_generate(
    output_dir: Path = typer.Option(Path("docs"), "--output", "-o", help="Output directory for generated docs."),
) -> None:
    """Generate API documentation."""
    generator = APIDocsGenerator(output_dir=output_dir)
    cli_path = generator.generate_cli_docs()
    python_path = generator.generate_python_api_docs()
    plugin_path = generator.generate_plugin_docs()
    console.print(f"[green]Generated docs:[/green]")
    console.print(f"  CLI: {cli_path}")
    console.print(f"  Python API: {python_path}")
    console.print(f"  Plugin Dev: {plugin_path}")


# ------------------------------------------------------------------
# Validate sub-commands
# ------------------------------------------------------------------

@validate_app.command("preset")
def validate_preset(
    file: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Path to a preset .json file."),
) -> None:
    """Validate a preset JSON file."""
    passed, errors = PresetValidator.validate(file)
    if passed:
        console.print(f"[green]Preset is valid:[/green] {file}")
    else:
        console.print(f"[red]Preset validation failed:[/red] {file}")
        for err in errors:
            console.print(f"  - {err}")
        raise typer.Exit(code=1)


@validate_app.command("plugin")
def validate_plugin(
    file: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Path to a plugin .py file."),
) -> None:
    """Validate a plugin file."""
    passed, errors = PluginValidator.validate(file)
    if passed:
        console.print(f"[green]Plugin is valid:[/green] {file}")
    else:
        console.print(f"[red]Plugin validation failed:[/red] {file}")
        for err in errors:
            console.print(f"  - {err}")
        raise typer.Exit(code=1)


# ------------------------------------------------------------------
# Contrib sub-commands
# ------------------------------------------------------------------

@contrib_app.command("guide")
def contrib_guide(
    output: Path = typer.Option(Path("CONTRIBUTING.md"), "--output", "-o", help="Output path for the guide."),
) -> None:
    """Generate a CONTRIBUTING.md template."""
    ContributionGuideGenerator.generate(output)
    console.print(f"[green]Generated contribution guide:[/green] {output}")


# ------------------------------------------------------------------
# Queue sub-commands
# ------------------------------------------------------------------

@queue_app.command("add")
def queue_add(
    input_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Input bitmap image."),
    output: Path = typer.Option(..., "--output", help="Output SVG path."),
    preset: str = typer.Option("poster", "--preset", "-p", help="Preset to use."),
) -> None:
    """Add a single conversion task to the persistent queue."""
    from .history import record_task

    opts = options_from_preset(preset)
    # For the CLI we run immediately in a one-shot queue so the user gets feedback.
    q = TaskQueue(max_workers=1)
    task_id = q.add_task(input_path, output, opts)
    q.start()
    task = q.wait_for(task_id)

    if task.status == "completed" and task.result:
        console.print(f"[green]Done[/green] {task.result.svg_path}")
        console.print(f"Engine: {task.result.engine} | Time: {task.result.elapsed_seconds:.2f}s")
        console.print(f"Stats: {task.result.stats}")
        record_task(task.result, preset, opts)
    elif task.status == "failed":
        console.print(f"[red]Failed:[/red] {task.error}")
        raise typer.Exit(code=1)


@queue_app.command("status")
def queue_status() -> None:
    """Show the status of tasks in the active queue."""
    console.print("[yellow]No persistent queue is running.[/yellow]")
    console.print("Use 'vector-studio queue add <file>' to process tasks immediately.")


@queue_app.command("start")
def queue_start() -> None:
    """Start processing the task queue."""
    console.print("[yellow]Queue start is handled automatically by 'queue add'.[/yellow]")


@queue_app.command("report")
def queue_report(
    path: Path = typer.Option(..., "--path", help="Output CSV path for the report."),
) -> None:
    """Export a report of queue tasks."""
    console.print("[yellow]No persistent queue state available.[/yellow]")
    console.print("Run 'vector-studio queue add' commands first.")


# ------------------------------------------------------------------
# Market sub-commands
# ------------------------------------------------------------------

@market_app.command("list")
def market_list() -> None:
    """List available presets from the market."""
    from .market import PresetMarket

    market = PresetMarket()
    presets = market.discover_presets()
    if not presets:
        console.print("[yellow]No presets found in the market.[/yellow]")
        console.print("Check your network connection or configure market sources.")
        return

    table = Table(title="Market Presets")
    table.add_column("ID", style="bold")
    table.add_column("Name")
    table.add_column("Author")
    table.add_column("Version")
    table.add_column("Tags")
    table.add_column("Rating")
    table.add_column("Downloads")

    for p in presets:
        table.add_row(
            p.get("id", "-"),
            p.get("display_name", p.get("name", "-")),
            p.get("author", "-"),
            p.get("version", "-"),
            ", ".join(p.get("tags", [])) or "-",
            str(p.get("rating", "-")),
            str(p.get("downloads", "-")),
        )
    console.print(table)


@market_app.command("search")
def market_search(
    query: str = typer.Argument(..., help="Search query."),
) -> None:
    """Search for presets in the market."""
    from .market import PresetMarket

    market = PresetMarket()
    presets = market.search(query)
    if not presets:
        console.print(f"[yellow]No presets found for '{query}'.[/yellow]")
        return

    table = Table(title=f"Search Results: {query}")
    table.add_column("ID", style="bold")
    table.add_column("Name")
    table.add_column("Author")
    table.add_column("Tags")

    for p in presets:
        table.add_row(
            p.get("id", "-"),
            p.get("display_name", p.get("name", "-")),
            p.get("author", "-"),
            ", ".join(p.get("tags", [])) or "-",
        )
    console.print(table)


@market_app.command("install")
def market_install(
    preset_id: str = typer.Argument(..., help="Preset ID to install."),
    name: str | None = typer.Option(None, "--name", "-n", help="Local name override."),
) -> None:
    """Install a preset from the market."""
    from .market import PresetMarket

    market = PresetMarket()
    try:
        local_name = market.install(preset_id, name=name)
        console.print(f"[green]Installed preset:[/green] {local_name}")
    except Exception as exc:
        console.print(f"[red]Installation failed:[/red] {exc}")
        raise typer.Exit(code=1)


@market_app.command("publish")
def market_publish(
    preset_name: str = typer.Argument(..., help="Local preset name to publish."),
    token: str | None = typer.Option(None, "--token", help="GitHub personal access token."),
) -> None:
    """Publish a local preset to the market."""
    from .market import PresetMarket

    auth_token = token or os.environ.get("GITHUB_TOKEN")
    if not auth_token:
        console.print(
            "[red]GitHub token required.[/red] Use --token or set GITHUB_TOKEN environment variable."
        )
        raise typer.Exit(code=1)

    market = PresetMarket()
    try:
        preset_id = market.publish(preset_name, auth_token)
        console.print(f"[green]Published preset:[/green] {preset_id}")
    except Exception as exc:
        console.print(f"[red]Publish failed:[/red] {exc}")
        raise typer.Exit(code=1)


@market_app.command("popular")
def market_popular(
    limit: int = typer.Option(10, "--limit", "-l", min=1, max=50, help="Number of presets to show."),
) -> None:
    """Show popular presets from the market."""
    from .market import PresetMarket

    market = PresetMarket()
    presets = market.get_popular(limit=limit)
    if not presets:
        console.print("[yellow]No popular presets found.[/yellow]")
        return

    table = Table(title="Popular Presets")
    table.add_column("ID", style="bold")
    table.add_column("Name")
    table.add_column("Rating")
    table.add_column("Downloads")

    for p in presets:
        table.add_row(
            p.get("id", "-"),
            p.get("display_name", p.get("name", "-")),
            str(p.get("rating", "-")),
            str(p.get("downloads", "-")),
        )
    console.print(table)


@market_app.command("info")
def market_info(
    preset_id: str = typer.Argument(..., help="Preset ID to inspect."),
) -> None:
    """Show detailed information about a market preset."""
    from .market import PresetMarket

    market = PresetMarket()
    try:
        preset = market.backend.download_preset(preset_id)
    except Exception as exc:
        console.print(f"[red]Failed to fetch preset:[/red] {exc}")
        raise typer.Exit(code=1)

    table = Table(title=f"Preset: {preset.get('display_name', preset_id)}")
    table.add_column("Property", style="bold")
    table.add_column("Value")

    for key in [
        "id",
        "name",
        "display_name",
        "description",
        "author",
        "version",
        "tags",
        "downloads",
        "rating",
        "created_at",
    ]:
        value = preset.get(key, "-")
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        table.add_row(key, str(value))
    console.print(table)


# ------------------------------------------------------------------
# Cloud market sub-commands (extends market)
# ------------------------------------------------------------------

@market_app.command("purchase")
def market_purchase(
    item_id: str = typer.Argument(..., help="Item ID to purchase."),
) -> None:
    """Purchase an item from the cloud market."""
    auth = load_auth()
    if not auth.get("token"):
        console.print("[red]Not logged in.[/red] Use 'vector-studio account login <token>'")
        raise typer.Exit(code=1)

    user_id = auth.get("user_id")
    if not user_id:
        console.print("[red]User ID not available.[/red] Run 'vector-studio account info' first.")
        raise typer.Exit(code=1)

    market = CloudMarket(auth.get("backend_url", "https://api.bitmap-vector-studio.example"))
    market.set_token(auth["token"])
    try:
        result = market.purchase_item(user_id, item_id)
        if result.get("success"):
            console.print(f"[green]Purchased[/green] {item_id}")
            remaining = result.get("remaining_credits")
            if remaining is not None:
                console.print(f"Remaining credits: {remaining}")
        else:
            console.print(f"[red]Purchase failed:[/red] {result.get('error', 'Unknown error')}")
            raise typer.Exit(code=1)
    except Exception as exc:
        console.print(f"[red]Purchase failed:[/red] {exc}")
        raise typer.Exit(code=1)


@market_app.command("library")
def market_library() -> None:
    """Show the user's purchased cloud market library."""
    auth = load_auth()
    if not auth.get("token"):
        console.print("[red]Not logged in.[/red] Use 'vector-studio account login <token>'")
        raise typer.Exit(code=1)

    user_id = auth.get("user_id")
    if not user_id:
        console.print("[red]User ID not available.[/red] Run 'vector-studio account info' first.")
        raise typer.Exit(code=1)

    market = CloudMarket(auth.get("backend_url", "https://api.bitmap-vector-studio.example"))
    market.set_token(auth["token"])
    try:
        items = market.get_user_library(user_id)
    except Exception as exc:
        console.print(f"[red]Failed to fetch library:[/red] {exc}")
        raise typer.Exit(code=1)

    if not items:
        console.print("[yellow]Your library is empty.[/yellow]")
        return

    table = Table(title="Your Library")
    table.add_column("Item ID", style="bold")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Purchased At")
    for item in items:
        table.add_row(
            item.get("item_id", "-"),
            item.get("name", "-"),
            item.get("item_type", "-"),
            item.get("purchased_at", "-"),
        )
    console.print(table)


@market_app.command("publish-item")
def market_publish_item(
    file: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Item JSON file to publish."),
    item_type: str = typer.Option("plugin", "--type", "-t", help="Item type: plugin, preset, etc."),
    name: str = typer.Option(..., "--name", "-n", help="Display name for the item."),
) -> None:
    """Publish an item file to the cloud market."""
    auth = load_auth()
    if not auth.get("token"):
        console.print("[red]Not logged in.[/red] Use 'vector-studio account login <token>'")
        raise typer.Exit(code=1)

    user_id = auth.get("user_id")
    if not user_id:
        console.print("[red]User ID not available.[/red] Run 'vector-studio account info' first.")
        raise typer.Exit(code=1)

    try:
        item_data = json.loads(file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        console.print(f"[red]Invalid JSON file:[/red] {exc}")
        raise typer.Exit(code=1)

    item_data["name"] = name
    item_data["file_name"] = file.name

    market = CloudMarket(auth.get("backend_url", "https://api.bitmap-vector-studio.example"))
    market.set_token(auth["token"])
    try:
        item_id = market.publish_item(user_id, item_type, item_data)
        if item_id:
            console.print(f"[green]Published[/green] {item_id}")
        else:
            console.print("[red]Publish failed.[/red]")
            raise typer.Exit(code=1)
    except Exception as exc:
        console.print(f"[red]Publish failed:[/red] {exc}")
        raise typer.Exit(code=1)


# ------------------------------------------------------------------
# Account sub-commands
# ------------------------------------------------------------------

@account_app.command("login")
def account_login(
    token: str = typer.Argument(..., help="Authentication token."),
    backend_url: str = typer.Option("https://api.bitmap-vector-studio.example", "--backend-url", help="Cloud backend URL."),
) -> None:
    """Log in to the cloud account using a token."""
    save_auth(token, backend_url)
    console.print("[green]Logged in successfully.[/green]")


@account_app.command("info")
def account_info() -> None:
    """Display current cloud account information."""
    auth = load_auth()
    if not auth.get("token"):
        console.print("[red]Not logged in.[/red] Use 'vector-studio account login <token>'")
        raise typer.Exit(code=1)

    market = CloudMarket(auth.get("backend_url", "https://api.bitmap-vector-studio.example"))
    market.set_token(auth["token"])
    try:
        user = market.get_current_user()
        if user.get("user_id") and not auth.get("user_id"):
            auth["user_id"] = user["user_id"]
            save_auth(auth["token"], auth["backend_url"], auth["user_id"])
    except Exception as exc:
        console.print(f"[red]Failed to fetch account info:[/red] {exc}")
        raise typer.Exit(code=1)

    table = Table(title="Account Information")
    table.add_column("Property", style="bold")
    table.add_column("Value")
    table.add_row("User ID", user.get("user_id", "-"))
    table.add_row("Username", user.get("username", "-"))
    table.add_row("Email", user.get("email", "-"))
    table.add_row("Tier", user.get("tier", "-"))
    table.add_row("Credits", str(user.get("credits", 0)))
    console.print(table)


@account_app.command("credits")
def account_credits() -> None:
    """Display current credit balance."""
    auth = load_auth()
    if not auth.get("token"):
        console.print("[red]Not logged in.[/red] Use 'vector-studio account login <token>'")
        raise typer.Exit(code=1)

    user_id = auth.get("user_id")
    if not user_id:
        console.print("[red]User ID not available.[/red] Run 'vector-studio account info' first.")
        raise typer.Exit(code=1)

    cs = CreditSystem(auth.get("backend_url", "https://api.bitmap-vector-studio.example"))
    cs.set_token(auth["token"])
    try:
        balance = cs.get_balance(user_id)
    except Exception as exc:
        console.print(f"[red]Failed to fetch credits:[/red] {exc}")
        raise typer.Exit(code=1)

    console.print(f"Credit balance: [green]{balance}[/green]")


# ------------------------------------------------------------------
# OCR sub-commands
# ------------------------------------------------------------------

@ocr_app.command("detect")
def ocr_detect(
    input_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Input bitmap image."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output JSON path for regions."),
    vertical: bool = typer.Option(False, "--vertical", help="Detect vertical text orientation."),
) -> None:
    """Detect text regions in an image."""
    from PIL import Image
    from .ai_ocr import detect_text_regions, detect_vertical_text

    with Image.open(input_path) as img:
        if vertical:
            regions = detect_vertical_text(img)
        else:
            regions = detect_text_regions(img)

    if output:
        import json
        output.write_text(json.dumps(regions, indent=2, ensure_ascii=False), encoding="utf-8")
        console.print(f"[green]Saved[/green] {output} ({len(regions)} regions)")
    else:
        table = Table(title=f"Text regions: {input_path.name}")
        table.add_column("#", style="bold")
        table.add_column("BBox")
        table.add_column("Confidence")
        table.add_column("Vertical")
        for idx, r in enumerate(regions, start=1):
            table.add_row(
                str(idx),
                f"{r['bbox']}",
                f"{r.get('confidence', 0):.3f}",
                "yes" if r.get("vertical") else "no",
            )
        console.print(table)


@ocr_app.command("recognize")
def ocr_recognize(
    input_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Input bitmap image."),
    lang: Optional[str] = typer.Option(None, "--lang", "-l", help="OCR language code (e.g. chi_sim, jpn, kor)."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output JSON path for results."),
) -> None:
    """Recognize text in an image with optional language support."""
    from PIL import Image
    from .ai_ocr import recognize_text_multilang

    with Image.open(input_path) as img:
        results = recognize_text_multilang(img, lang=lang)

    if output:
        import json
        output.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        console.print(f"[green]Saved[/green] {output} ({len(results)} lines)")
    else:
        table = Table(title=f"OCR results: {input_path.name}")
        table.add_column("#", style="bold")
        table.add_column("Text")
        table.add_column("BBox")
        table.add_column("Confidence")
        table.add_column("Lang")
        for idx, r in enumerate(results, start=1):
            table.add_row(
                str(idx),
                r.get("text", "") or "-",
                f"{r['bbox']}",
                f"{r.get('confidence', 0):.3f}",
                r.get("lang", "eng"),
            )
        console.print(table)


@ocr_app.command("languages")
def ocr_languages() -> None:
    """List available OCR languages and their installation status."""
    installed = get_tesseract_languages()
    table = Table(title="OCR Languages")
    table.add_column("Code", style="bold")
    table.add_column("Name")
    table.add_column("Tesseract")
    table.add_column("Installed")
    for code, cfg in sorted(OCR_LANGUAGE_CONFIG.items()):
        tess = cfg["tesseract_code"]
        is_installed = "yes" if tess in installed else "no"
        table.add_row(code, cfg["name"], tess, is_installed)
    console.print(table)
    if not installed:
        console.print("[yellow]No Tesseract language packs detected.[/yellow]")
        console.print("Install Tesseract and language packs to use OCR.")


# ------------------------------------------------------------------
# AI sub-commands
# ------------------------------------------------------------------

@ai_app.command("segment")
def ai_segment(
    input_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Input bitmap image."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output PNG path."),
    model: str = typer.Option("unet-lite", "--model", help="Segmentation model name."),
) -> None:
    """Segment an image into foreground/background."""
    from PIL import Image
    from vector_studio.ai_onnx import ImageSegmenter

    segmenter = ImageSegmenter()
    with Image.open(input_path) as img:
        mask = segmenter.segment(img, model_name=model)

    out = output or input_path.with_stem(input_path.stem + "_mask")
    if out.suffix.lower() != ".png":
        out = out.with_suffix(".png")
    mask.save(out, format="PNG", optimize=True)
    console.print(f"[green]Saved mask[/green] {out}")


@ai_app.command("style")
def ai_style(
    input_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Input bitmap image."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output PNG path."),
    style: str = typer.Option("sketch", "--style", help="Style: sketch, oil, watercolor, cartoon."),
) -> None:
    """Apply artistic style transfer to an image."""
    from PIL import Image
    from vector_studio.ai_onnx import StyleTransfer

    transfer = StyleTransfer()
    with Image.open(input_path) as img:
        styled = transfer.transfer(img, style=style)

    out = output or input_path.with_stem(input_path.stem + f"_{style}")
    if out.suffix.lower() != ".png":
        out = out.with_suffix(".png")
    styled.save(out, format="PNG", optimize=True)
    console.print(f"[green]Saved styled image[/green] {out}")


@ai_app.command("upscale")
def ai_upscale(
    input_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Input bitmap image."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output PNG path."),
    scale: int = typer.Option(2, "--scale", min=1, max=4, help="Upscaling factor."),
) -> None:
    """Upscale an image using super-resolution."""
    from PIL import Image
    from vector_studio.ai_onnx import SuperResolution

    sr = SuperResolution()
    with Image.open(input_path) as img:
        upscaled = sr.upscale(img, scale=scale)

    out = output or input_path.with_stem(input_path.stem + f"_x{scale}")
    if out.suffix.lower() != ".png":
        out = out.with_suffix(".png")
    upscaled.save(out, format="PNG", optimize=True)
    console.print(f"[green]Saved upscaled image[/green] {out} ({upscaled.size[0]}x{upscaled.size[1]})")


@ai_app.command("models")
def ai_models() -> None:
    """List available ONNX models and their download status."""
    from vector_studio.ai_onnx import MODEL_REGISTRY, ONNXModelManager

    manager = ONNXModelManager()
    available = {m["name"] for m in manager.list_available_models()}

    table = Table(title="ONNX Models")
    table.add_column("Name", style="bold")
    table.add_column("Description")
    table.add_column("Size (MB)")
    table.add_column("Downloaded")

    for name, meta in sorted(MODEL_REGISTRY.items()):
        downloaded = "yes" if name in available else "no"
        table.add_row(name, meta["description"], str(meta["size_mb"]), downloaded)
    console.print(table)


@ai_app.command("download")
def ai_download(
    model: str = typer.Argument(..., help="Model name to download."),
    url: Optional[str] = typer.Option(None, "--url", help="Override download URL."),
) -> None:
    """Download an ONNX model."""
    from vector_studio.ai_onnx import ONNXModelManager

    manager = ONNXModelManager()
    try:
        path = manager.download_model(model, url=url)
        console.print(f"[green]Downloaded[/green] {model} → {path}")
    except Exception as exc:
        console.print(f"[red]Download failed:[/red] {exc}")
        raise typer.Exit(code=1)


# ------------------------------------------------------------------
# Generate sub-commands
# ------------------------------------------------------------------

@generate_app.command("text")
def generate_text(
    prompt: str = typer.Argument(..., help="Text prompt for the image."),
    style: str = typer.Option("flat", "--style", "-s", help="Style: flat, line, gradient, 3d, sketch."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output PNG path."),
    width: int = typer.Option(512, "--width", min=64, max=2048, help="Output width."),
    height: int = typer.Option(512, "--height", min=64, max=2048, help="Output height."),
) -> None:
    """Generate a vector-style image from a text prompt."""
    from vector_studio.ai_generation import VectorGenerator

    generator = VectorGenerator()
    img = generator.generate_from_text(prompt, style=style, size=(width, height))
    out = output or Path(f"generated_{style}.png")
    if out.suffix.lower() != ".png":
        out = out.with_suffix(".png")
    img.save(out, format="PNG", optimize=True)
    console.print(f"[green]Generated[/green] {out} ({img.size[0]}x{img.size[1]})")


@generate_app.command("image")
def generate_image(
    input_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Reference image."),
    prompt: Optional[str] = typer.Option(None, "--prompt", "-p", help="Optional text prompt."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output PNG path."),
) -> None:
    """Generate a new vector-style image based on a reference image."""
    from PIL import Image
    from vector_studio.ai_generation import VectorGenerator

    generator = VectorGenerator()
    with Image.open(input_path) as img:
        result = generator.generate_from_image(img, prompt=prompt)
    out = output or input_path.with_stem(input_path.stem + "_generated")
    if out.suffix.lower() != ".png":
        out = out.with_suffix(".png")
    result.save(out, format="PNG", optimize=True)
    console.print(f"[green]Generated[/green] {out} ({result.size[0]}x{result.size[1]})")


@generate_app.command("icon")
def generate_icon(
    prompt: str = typer.Argument(..., help="Text prompt for the icon."),
    style: str = typer.Option("flat", "--style", "-s", help="Style: flat, minimal, line, gradient."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output PNG path."),
) -> None:
    """Generate a square icon from a text prompt."""
    from vector_studio.ai_generation import VectorGenerator

    generator = VectorGenerator()
    img = generator.generate_icon(prompt, style=style)
    out = output or Path(f"icon_{style}.png")
    if out.suffix.lower() != ".png":
        out = out.with_suffix(".png")
    img.save(out, format="PNG", optimize=True)
    console.print(f"[green]Generated icon[/green] {out} ({img.size[0]}x{img.size[1]})")


@generate_app.command("logo")
def generate_logo(
    prompt: str = typer.Argument(..., help="Text prompt for the logo."),
    style: str = typer.Option("minimal", "--style", "-s", help="Style: minimal, modern, flat."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output PNG path."),
) -> None:
    """Generate a logo from a text prompt."""
    from vector_studio.ai_generation import VectorGenerator

    generator = VectorGenerator()
    img = generator.generate_logo(prompt, style=style)
    out = output or Path(f"logo_{style}.png")
    if out.suffix.lower() != ".png":
        out = out.with_suffix(".png")
    img.save(out, format="PNG", optimize=True)
    console.print(f"[green]Generated logo[/green] {out} ({img.size[0]}x{img.size[1]})")


@generate_app.command("illustration")
def generate_illustration(
    prompt: str = typer.Argument(..., help="Text prompt for the illustration."),
    style: str = typer.Option("cartoon", "--style", "-s", help="Style: cartoon, watercolor, sketch."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output PNG path."),
) -> None:
    """Generate an illustration from a text prompt."""
    from vector_studio.ai_generation import VectorGenerator

    generator = VectorGenerator()
    img = generator.generate_illustration(prompt, style=style)
    out = output or Path(f"illustration_{style}.png")
    if out.suffix.lower() != ".png":
        out = out.with_suffix(".png")
    img.save(out, format="PNG", optimize=True)
    console.print(f"[green]Generated illustration[/green] {out} ({img.size[0]}x{img.size[1]})")


# ------------------------------------------------------------------
# Resume command
# ------------------------------------------------------------------

@app.command("resume", hidden=True)
def resume_command(
    checkpoint_id: str = typer.Argument("", help="Checkpoint ID to resume."),
    workers: int = typer.Option(1, "--workers", "-w", min=1, max=16, help="Number of concurrent workers."),
    retry: int = typer.Option(0, "--retry", min=0, max=5, help="Number of retries on failure."),
    list_checkpoints: bool = typer.Option(False, "--list", help="List available checkpoints."),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON."),
) -> None:
    """Resume an interrupted batch conversion from a checkpoint."""
    cp_mgr = CheckpointManager()

    if list_checkpoints:
        checkpoints = cp_mgr.list_checkpoints()
        if json_output:
            import json as _json
            console.print(_json.dumps(checkpoints, indent=2, ensure_ascii=False))
        else:
            table = Table(title="Checkpoints")
            table.add_column("Queue ID", style="bold")
            table.add_column("Saved At")
            table.add_column("Tasks")
            for cp in checkpoints:
                table.add_row(cp["queue_id"], cp.get("saved_at", "-"), str(cp.get("task_count", 0)))
            console.print(table)
        return

    if not checkpoint_id:
        console.print("[red]Error:[/red] checkpoint_id is required (or use --list)")
        raise typer.Exit(code=1)

    tasks = cp_mgr.load_checkpoint(checkpoint_id)
    if tasks is None:
        console.print(f"[red]No checkpoint found:[/red] {checkpoint_id}")
        raise typer.Exit(code=1)

    pending_tasks = [t for t in tasks if t.status in ("pending", "running", "failed")]
    if not pending_tasks:
        console.print("[green]All tasks in this checkpoint are already completed.[/green]")
        raise typer.Exit(code=0)

    q = TaskQueue(max_workers=workers, max_retries=retry, checkpoint_manager=cp_mgr, queue_id=checkpoint_id)
    with q._lock:
        for task in pending_tasks:
            task.status = "pending"
            task.progress = 0.0
            task.started_at = None
            q._tasks[task.task_id] = task
            q._queue.put(task)

    q.start()
    results = q.wait_for_all()

    table = Table(title=f"Resumed batch: {len(results)} task(s)")
    table.add_column("Input")
    table.add_column("Output")
    table.add_column("Status")

    failures = 0
    for task in results:
        if task.status == "completed":
            table.add_row(str(task.input_path), str(task.output_path), "ok")
        elif task.status == "failed":
            failures += 1
            table.add_row(str(task.input_path), str(task.output_path), f"failed: {task.error}")
        else:
            table.add_row(str(task.input_path), str(task.output_path), task.status)

    console.print(table)
    if failures:
        raise typer.Exit(code=1)
    # Clean up checkpoint on full success.
    cp_mgr.delete_checkpoint(checkpoint_id)


# ------------------------------------------------------------------
# Workspace sub-commands
# ------------------------------------------------------------------

@workspace_app.command("list")
def workspace_list() -> None:
    """List all saved workspaces."""
    manager = WorkspaceManager()
    workspaces = manager.list_workspaces()
    if not workspaces:
        console.print("[yellow]No saved workspaces.[/yellow]")
        return
    table = Table(title="Workspaces")
    table.add_column("Name", style="bold")
    table.add_column("Timestamp")
    for ws in workspaces:
        table.add_row(ws["name"], ws.get("timestamp", "-"))
    console.print(table)


@workspace_app.command("save")
def workspace_save(
    name: Optional[str] = typer.Argument(None, help="Workspace name. Defaults to timestamp."),
    open_files: list[str] = typer.Option([], "--open-file", help="File paths currently open."),
    preset: str = typer.Option("poster", "--preset", help="Current preset."),
) -> None:
    """Save the current workspace."""
    manager = WorkspaceManager()
    ws = Workspace(
        open_files=open_files,
        current_preset=preset,
    )
    path = manager.save(ws, name=name)
    console.print(f"[green]Workspace saved:[/green] {path.name}")


@workspace_app.command("load")
def workspace_load(
    name: str = typer.Argument(..., help="Workspace name to load."),
) -> None:
    """Load a saved workspace."""
    manager = WorkspaceManager()
    ws = manager.load(name)
    if ws is None:
        console.print(f"[red]Workspace not found:[/red] {name}")
        raise typer.Exit(code=1)
    console.print(f"[green]Loaded workspace[/green] {name}")
    console.print(f"Preset: {ws.current_preset}")
    console.print(f"Open files: {', '.join(ws.open_files) or 'none'}")


@workspace_app.command("delete")
def workspace_delete(
    name: str = typer.Argument(..., help="Workspace name to delete."),
) -> None:
    """Delete a saved workspace."""
    manager = WorkspaceManager()
    if manager.delete(name):
        console.print(f"[green]Deleted workspace[/green] {name}")
    else:
        console.print(f"[red]Workspace not found:[/red] {name}")
        raise typer.Exit(code=1)


# ------------------------------------------------------------------
# Cloud sync sub-commands
# ------------------------------------------------------------------

def _get_cloud_manager(backend: str | None = None, base_url: str = "http://localhost:8000") -> CloudSyncManager:
    """Build a CloudSyncManager from CLI options."""
    if backend == "gist":
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            console.print("[red]GITHUB_TOKEN environment variable is required for Gist backend.[/red]")
            raise typer.Exit(code=1)
        gb = GitHubGistBackend(token=token)
        return CloudSyncManager(backend=gb)
    # Default local backend
    import tempfile
    tmpdir = Path(tempfile.mkdtemp(prefix="vs-cloud-cli-"))
    lb = LocalServerBackend(storage_dir=tmpdir, base_url=base_url)
    return CloudSyncManager(backend=lb)


@cloud_app.command("share")
def cloud_share(
    svg: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="SVG file to share."),
    expire_hours: int = typer.Option(24, "--expire", "-e", min=1, max=168, help="Expiration time in hours."),
    backend: str = typer.Option("local", "--backend", "-b", help="Backend: local or gist."),
    base_url: str = typer.Option("http://localhost:8000", "--base-url", help="Base URL for local shares."),
) -> None:
    """Share an SVG file and display the link and QR code."""
    manager = _get_cloud_manager(backend=backend, base_url=base_url)
    try:
        result = manager.share_svg(svg, expire_hours=expire_hours)
    except Exception as exc:
        console.print(f"[red]Share failed:[/red] {exc}")
        raise typer.Exit(code=1)

    console.print(f"[green]Shared[/green] {svg.name}")
    console.print(f"URL: {result['url']}")
    console.print(f"Expires: {result['expire_at']}")
    console.print(f"File ID: {result['file_id']}")
    # Print a small ASCII hint that QR data is available.
    console.print(f"QR code (base64, {len(result['qr_code'])} chars)")


@cloud_app.command("list")
def cloud_list(
    backend: str = typer.Option("local", "--backend", "-b", help="Backend: local or gist."),
    base_url: str = typer.Option("http://localhost:8000", "--base-url", help="Base URL for local shares."),
) -> None:
    """List all shared files."""
    manager = _get_cloud_manager(backend=backend, base_url=base_url)
    shares = manager.get_shared_files()
    if not shares:
        console.print("[yellow]No active shares.[/yellow]")
        return

    table = Table(title="Shared Files")
    table.add_column("File ID", style="bold")
    table.add_column("URL")
    table.add_column("Expires")
    for share in shares:
        sid = share.get("share_id", share.get("file_id", "-"))
        url = share.get("url", "-")
        exp = share.get("expire_at", "-")
        table.add_row(sid, url, exp)
    console.print(table)


@cloud_app.command("revoke")
def cloud_revoke(
    file_id: str = typer.Argument(..., help="File ID to revoke."),
    backend: str = typer.Option("local", "--backend", "-b", help="Backend: local or gist."),
    base_url: str = typer.Option("http://localhost:8000", "--base-url", help="Base URL for local shares."),
) -> None:
    """Revoke a shared file."""
    manager = _get_cloud_manager(backend=backend, base_url=base_url)
    success = manager.revoke_share(file_id)
    if success:
        console.print(f"[green]Revoked share[/green] {file_id}")
    else:
        console.print(f"[red]Share not found:[/red] {file_id}")
        raise typer.Exit(code=1)


@cloud_app.command("qr")
def cloud_qr(
    file_id: str = typer.Argument(..., help="File ID to generate QR for."),
    backend: str = typer.Option("local", "--backend", "-b", help="Backend: local or gist."),
    base_url: str = typer.Option("http://localhost:8000", "--base-url", help="Base URL for local shares."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output PNG path."),
) -> None:
    """Generate a QR code PNG for a shared file."""
    manager = _get_cloud_manager(backend=backend, base_url=base_url)
    try:
        qr_bytes = manager.backend.get_qr_code(file_id)
    except Exception as exc:
        console.print(f"[red]QR generation failed:[/red] {exc}")
        raise typer.Exit(code=1)

    if output:
        output.write_bytes(qr_bytes)
        console.print(f"[green]Saved QR code[/green] {output}")
    else:
        # Print base64 to stdout so it can be piped.
        import base64
        console.print(base64.b64encode(qr_bytes).decode("ascii"))


# ------------------------------------------------------------------
# Engine sub-commands
# ------------------------------------------------------------------

@engine_app.command("list")
def engine_list() -> None:
    """List all registered vectorization engines and their availability."""
    from .engines import EngineRegistry

    registry = EngineRegistry()
    engines = registry.list_engines()

    table = Table(title="Vectorization Engines")
    table.add_column("Name", style="bold")
    table.add_column("Version")
    table.add_column("Available")
    table.add_column("Formats")
    table.add_column("Outputs")

    for info in engines:
        table.add_row(
            info["name"],
            info["version"],
            "yes" if info["available"] else "no",
            ", ".join(info["supported_formats"]) or "-",
            ", ".join(info["supported_outputs"]) or "-",
        )
    console.print(table)


@engine_app.command("info")
def engine_info(
    name: str = typer.Argument(..., help="Engine name: vtracer, potrace, autotrace."),
) -> None:
    """Show detailed information about a specific engine."""
    from .engines import EngineRegistry

    registry = EngineRegistry()
    try:
        instance = registry.get_engine(name)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    info = instance.get_info()
    table = Table(title=f"Engine: {info['name']}")
    table.add_column("Property", style="bold")
    table.add_column("Value")
    table.add_row("Name", info["name"])
    table.add_row("Version", info["version"])
    table.add_row("Available", "yes" if info["available"] else "no")
    table.add_row("Supported inputs", ", ".join(info["supported_formats"]))
    table.add_row("Supported outputs", ", ".join(info["supported_outputs"]))
    console.print(table)


@engine_app.command("benchmark")
def engine_benchmark(
    input_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Input bitmap image."),
    engines: list[str] = typer.Option([], "--engine", "-e", help="Engine(s) to benchmark. Omit to test all available."),
    preset: str = typer.Option("poster", "--preset", "-p", help="Preset to use for VTracer-based engines."),
) -> None:
    """Compare multiple engines on the same image."""
    from .engines import EngineBenchmark, EngineRegistry
    from .presets import options_from_preset

    opts = options_from_preset(preset)
    benchmark = EngineBenchmark()
    engine_list = engines if engines else None

    results = benchmark.compare_engines(input_path, engines=engine_list, options={"trace_options": opts})

    table = Table(title=f"Engine Benchmark: {input_path.name}")
    table.add_column("Engine", style="bold")
    table.add_column("Time (s)")
    table.add_column("Size (bytes)")
    table.add_column("Paths")
    table.add_column("Quality")
    table.add_column("Status")

    for r in results:
        if "error" in r:
            table.add_row(
                r["engine"],
                "-",
                "-",
                "-",
                "-",
                f"error: {r['error']}",
            )
        else:
            table.add_row(
                r["engine"],
                f"{r.get('elapsed_seconds', 0):.3f}",
                str(r.get("file_bytes", 0)),
                str(r.get("paths", 0)),
                str(r.get("quality_score", "-")),
                "ok",
            )
    console.print(table)


@engine_app.command("auto")
def engine_auto(
    input_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Input bitmap image."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output SVG path."),
    preset: str = typer.Option("poster", "--preset", "-p", help="Preset to use."),
) -> None:
    """Automatically select the best engine for the given image and convert it."""
    from .engines import EngineRegistry
    from .presets import options_from_preset

    registry = EngineRegistry()
    best_engine = registry.get_best_engine(input_path)
    info = best_engine.get_info()
    console.print(f"[cyan]Recommended engine:[/cyan] {info['name']} (available={info['available']})")

    opts = options_from_preset(preset)
    out = output or input_path.with_suffix(".svg")

    result = trace_image(
        input_path,
        out,
        opts,
        engine=info["name"],
    )
    console.print(f"[green]Done[/green] {result.svg_path}")
    console.print(f"Engine: {result.engine} | Time: {result.elapsed_seconds:.2f}s")
    console.print(f"Stats: {result.stats}")


@collab_app.command("create")
def collab_create(
    owner: str = typer.Option("anonymous", "--owner", "-o", help="Room owner identifier."),
    api_url: str = typer.Option("http://localhost:8000", "--api-url", help="Base URL of the API server."),
) -> None:
    """Create a new collaboration room."""
    import urllib.request
    import urllib.error
    import json as _json

    url = f"{api_url}/collab/rooms?owner={urllib.parse.quote(owner)}"
    try:
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        console.print(f"[red]API error:[/red] {exc.code} {exc.reason}")
        raise typer.Exit(code=1)
    except Exception as exc:
        console.print(f"[red]Failed to create room:[/red] {exc}")
        raise typer.Exit(code=1)

    console.print(f"[green]Created room[/green] {data['room_id']}")
    console.print(f"Owner: {data['owner']}")
    console.print(f"Created at: {data['created_at']}")


@collab_app.command("join")
def collab_join(
    room_id: str = typer.Argument(..., help="Room identifier to join."),
    client_id: str = typer.Option("", "--client-id", "-c", help="Client identifier (auto-generated if empty)."),
    api_url: str = typer.Option("http://localhost:8000", "--api-url", help="Base URL of the API server."),
) -> None:
    """Join a collaboration room (CLI polling mode).

    In CLI mode we do not maintain a WebSocket; instead we print the
    current room state and exit. Use the desktop or web UI for real-time
    WebSocket collaboration.
    """
    import urllib.request
    import urllib.error
    import json as _json

    url = f"{api_url}/collab/rooms/{urllib.parse.quote(room_id)}"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            console.print(f"[red]Room not found:[/red] {room_id}")
        else:
            console.print(f"[red]API error:[/red] {exc.code} {exc.reason}")
        raise typer.Exit(code=1)
    except Exception as exc:
        console.print(f"[red]Failed to join room:[/red] {exc}")
        raise typer.Exit(code=1)

    console.print(f"[green]Joined room[/green] {data['room_id']}")
    console.print(f"Owner: {data['owner']} | Clients: {data['client_count']}")
    console.print(f"Operations: {data['operation_count']} | Next version: {data['next_version']}")
    if data.get("params"):
        console.print(f"Params: {data['params']}")
    if data.get("files"):
        console.print(f"Files: {len(data['files'])} file(s)")


@collab_app.command("status")
def collab_status(
    room_id: str = typer.Argument(..., help="Room identifier."),
    api_url: str = typer.Option("http://localhost:8000", "--api-url", help="Base URL of the API server."),
) -> None:
    """Show the current status of a collaboration room."""
    import urllib.request
    import urllib.error
    import json as _json

    url = f"{api_url}/collab/rooms/{urllib.parse.quote(room_id)}"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            console.print(f"[red]Room not found:[/red] {room_id}")
        else:
            console.print(f"[red]API error:[/red] {exc.code} {exc.reason}")
        raise typer.Exit(code=1)
    except Exception as exc:
        console.print(f"[red]Failed to get status:[/red] {exc}")
        raise typer.Exit(code=1)

    table = Table(title=f"Room: {data['room_id']}")
    table.add_column("Property", style="bold")
    table.add_column("Value")
    table.add_row("Owner", data["owner"])
    table.add_row("Created", data["created_at"])
    table.add_row("Clients", str(data["client_count"]))
    table.add_row("Operations", str(data["operation_count"]))
    table.add_row("Next version", str(data["next_version"]))
    console.print(table)

    if data.get("params"):
        console.print(f"[cyan]Params:[/cyan] {data['params']}")
    if data.get("last_convert"):
        console.print(f"[cyan]Last convert:[/cyan] {data['last_convert']}")


@collab_app.command("history")
def collab_history(
    room_id: str = typer.Argument(..., help="Room identifier."),
    limit: int = typer.Option(20, "--limit", "-l", min=1, max=500, help="Number of operations to show."),
    api_url: str = typer.Option("http://localhost:8000", "--api-url", help="Base URL of the API server."),
) -> None:
    """Show the operation history of a collaboration room."""
    import urllib.request
    import urllib.error
    import json as _json

    url = f"{api_url}/collab/rooms/{urllib.parse.quote(room_id)}/history?limit={limit}"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            console.print(f"[red]Room not found:[/red] {room_id}")
        else:
            console.print(f"[red]API error:[/red] {exc.code} {exc.reason}")
        raise typer.Exit(code=1)
    except Exception as exc:
        console.print(f"[red]Failed to get history:[/red] {exc}")
        raise typer.Exit(code=1)

    ops = data.get("operations", [])
    if not ops:
        console.print("[yellow]No operations yet.[/yellow]")
        return

    table = Table(title=f"Operation History ({len(ops)} entries)")
    table.add_column("#", style="bold")
    table.add_column("Op ID")
    table.add_column("Client")
    table.add_column("Type")
    table.add_column("Version")
    for idx, op in enumerate(ops, start=1):
        table.add_row(
            str(idx),
            op.get("op_id", "-"),
            op.get("client_id", "-"),
            op.get("type", "-"),
            str(op.get("version", "-")),
        )
    console.print(table)


@sync_app.command("status")
def sync_status(
    server_url: str = typer.Option("http://localhost:8000", "--server-url", help="Sync server URL."),
) -> None:
    """Show the sync status for this device."""
    client = SyncClient(server_url=server_url)
    status = client.get_sync_status()
    table = Table(title="Sync Status")
    table.add_column("Property", style="bold")
    table.add_column("Value")
    for key, value in status.items():
        table.add_row(key, str(value))
    console.print(table)


# ------------------------------------------------------------------
# Workflow sub-commands
# ------------------------------------------------------------------

@workflow_app.command("list")
def workflow_list() -> None:
    """List built-in workflow templates."""
    table = Table(title="Workflow Templates")
    table.add_column("Name", style="bold")
    table.add_column("Description")
    templates = [
        ("logo_pipeline", "Input -> Background transparent -> Convert -> Optimize -> Export"),
        ("photo_pipeline", "Input -> AI enhance -> Convert -> Optimize -> Export"),
        ("batch_pipeline", "Input -> Loop -> Convert -> Merge -> Export"),
    ]
    for name, desc in templates:
        table.add_row(name, desc)
    console.print(table)


@workflow_app.command("run")
def workflow_run(
    workflow_file: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Workflow JSON file."),
    input_path: Path = typer.Option(..., "--input", "-i", exists=True, dir_okay=False, readable=True, help="Input image."),
    output_dir: Path = typer.Option(..., "--output-dir", "-o", help="Output directory."),
) -> None:
    """Run a workflow file against an input image."""
    try:
        workflow = Workflow.load(workflow_file)
    except Exception as exc:
        console.print(f"[red]Failed to load workflow:[/red] {exc}")
        raise typer.Exit(code=1)

    valid, errors = workflow.validate()
    if not valid:
        for err in errors:
            console.print(f"[red]Validation error:[/red] {err}")
        raise typer.Exit(code=1)

    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        results = workflow.execute(input_path, output_dir)
    except Exception as exc:
        console.print(f"[red]Workflow execution failed:[/red] {exc}")
        raise typer.Exit(code=1)

    if results:
        console.print(f"[green]Workflow completed.[/green] {len(results)} output(s):")
        for p in results:
            console.print(f"  {p}")
    else:
        console.print("[yellow]Workflow produced no outputs.[/yellow]")


@workflow_app.command("create")
def workflow_create(
    template: str = typer.Option(..., "--template", "-t", help="Template name: logo_pipeline, photo_pipeline, batch_pipeline."),
    output: Path = typer.Option(Path("workflow.json"), "--output", "-o", help="Output workflow JSON file."),
) -> None:
    """Create a workflow from a built-in template."""
    try:
        workflow = WorkflowTemplate.get_template(template)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)
    workflow.save(output)
    console.print(f"[green]Created workflow:[/green] {output}")


@workflow_app.command("validate")
def workflow_validate(
    workflow_file: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Workflow JSON file."),
) -> None:
    """Validate a workflow file."""
    try:
        workflow = Workflow.load(workflow_file)
    except Exception as exc:
        console.print(f"[red]Failed to load workflow:[/red] {exc}")
        raise typer.Exit(code=1)

    valid, errors = workflow.validate()
    if valid:
        console.print(f"[green]Workflow is valid:[/green] {workflow_file.name}")
    else:
        console.print(f"[red]Workflow validation failed:[/red] {workflow_file.name}")
        for err in errors:
            console.print(f"  - {err}")
        raise typer.Exit(code=1)


# ------------------------------------------------------------------
# Sync sub-commands
# ------------------------------------------------------------------

@sync_app.command("push")
def sync_push(
    server_url: str = typer.Option("http://localhost:8000", "--server-url", help="Sync server URL."),
) -> None:
    """Push local data to the sync server."""
    client = SyncClient(server_url=server_url)
    results = client.push_all()
    table = Table(title="Sync Push Results")
    table.add_column("Data Type", style="bold")
    table.add_column("Status")
    for dtype, ok in results.items():
        status = "[green]ok[/green]" if ok else "[red]failed[/red]"
        table.add_row(dtype, status)
    console.print(table)
    if not all(results.values()):
        raise typer.Exit(code=1)


@sync_app.command("pull")
def sync_pull(
    server_url: str = typer.Option("http://localhost:8000", "--server-url", help="Sync server URL."),
) -> None:
    """Pull remote data from the sync server and merge with local copies."""
    client = SyncClient(server_url=server_url)
    merged: dict[str, Any] = {}
    try:
        merged["workspaces"] = client.sync_workspaces()
    except Exception as exc:
        console.print(f"[yellow]Workspaces sync failed:[/yellow] {exc}")
    try:
        merged["presets"] = client.sync_presets()
    except Exception as exc:
        console.print(f"[yellow]Presets sync failed:[/yellow] {exc}")
    try:
        merged["config"] = client.sync_config()
    except Exception as exc:
        console.print(f"[yellow]Config sync failed:[/yellow] {exc}")
    try:
        merged["history"] = client.sync_history()
    except Exception as exc:
        console.print(f"[yellow]History sync failed:[/yellow] {exc}")

    table = Table(title="Sync Pull Results")
    table.add_column("Data Type", style="bold")
    table.add_column("Count")
    for dtype, data in merged.items():
        count = len(data) if isinstance(data, list) else "-"
        table.add_row(dtype, str(count))
    console.print(table)


@sync_app.command("status")
def sync_status(
    server_url: str = typer.Option("http://localhost:8000", "--server-url", help="Sync server URL."),
) -> None:
    """Show the sync status for this device."""
    client = SyncClient(server_url=server_url)
    status = client.get_sync_status()
    table = Table(title="Sync Status")
    table.add_column("Property", style="bold")
    table.add_column("Value")
    for key, value in status.items():
        table.add_row(key, str(value))
    console.print(table)


# ------------------------------------------------------------------
# Animation sub-commands
# ------------------------------------------------------------------

@animate_app.command("svg")
def animate_svg(
    input_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Input SVG file."),
    output: Path = typer.Option(..., "--output", "-o", help="Output animated SVG path."),
    preset: str = typer.Option("draw", "--preset", "-p", help="Animation preset: draw, reveal, morph, pulse, color_cycle."),
) -> None:
    """Export an SVG with embedded SMIL animations."""
    builder = AnimationBuilder().load_svg(input_path).apply_preset(preset)
    builder.export("smil", output)
    console.print(f"[green]Animated SVG exported:[/green] {output}")


@animate_app.command("lottie")
def animate_lottie(
    input_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Input SVG file."),
    output: Path = typer.Option(..., "--output", "-o", help="Output Lottie JSON path."),
) -> None:
    """Convert an SVG to Lottie JSON format."""
    exporter = LottieExporter(input_path)
    exporter.export_lottie(output)
    console.print(f"[green]Lottie exported:[/green] {output}")


@animate_app.command("gif")
def animate_gif(
    input_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Input SVG file."),
    output: Path = typer.Option(..., "--output", "-o", help="Output GIF path."),
    fps: int = typer.Option(30, "--fps", min=1, max=60, help="Frames per second."),
    duration: float = typer.Option(2.0, "--duration", min=0.1, max=10.0, help="Animation duration in seconds."),
    preset: str = typer.Option("draw", "--preset", "-p", help="Animation preset."),
) -> None:
    """Export a GIF preview of an SVG animation."""
    builder = AnimationBuilder().load_svg(input_path).apply_preset(preset)
    builder.export("gif", output)
    console.print(f"[green]GIF exported:[/green] {output} ({fps} fps, {duration}s)")


@animate_app.command("presets")
def animate_presets() -> None:
    """List available animation presets."""
    names = list_animation_presets()
    table = Table(title="Animation Presets")
    table.add_column("Name", style="bold")
    table.add_column("Description")
    descriptions = {
        "draw": "Stroke draw animation using dash-offset",
        "reveal": "Fade-in reveal animation",
        "morph": "Path morphing between shapes",
        "pulse": "Color pulse with fade",
        "color_cycle": "Cyclic color transition",
    }
    for name in names:
        table.add_row(name, descriptions.get(name, "-"))
    console.print(table)


# ------------------------------------------------------------------
# Design sub-commands
# ------------------------------------------------------------------

@design_app.command("figma-export")
def design_figma_export(
    svg: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="SVG file to export."),
    file_key: str = typer.Option(..., "--file-key", help="Figma file key."),
    node_id: str = typer.Option("", "--node-id", help="Target node id."),
) -> None:
    """Export an SVG to a Figma file."""
    plugin = FigmaPlugin()
    success = plugin.export_to_figma(svg, file_key, node_id)
    if success:
        console.print(f"[green]Exported[/green] {svg.name} to Figma {file_key}")
    else:
        console.print(f"[red]Export failed.[/red] Check FIGMA_TOKEN and file permissions.")
        raise typer.Exit(code=1)


@design_app.command("figma-import")
def design_figma_import(
    file_key: str = typer.Option(..., "--file-key", help="Figma file key."),
    node_id: str = typer.Option(..., "--node-id", help="Node id to import."),
    output: Path = typer.Option(None, "--output", "-o", help="Output SVG path."),
) -> None:
    """Import a Figma node as an SVG."""
    plugin = FigmaPlugin()
    try:
        path = plugin.import_from_figma(file_key, node_id)
        if output:
            import shutil
            shutil.move(str(path), str(output))
            path = output
        console.print(f"[green]Imported[/green] {path}")
    except Exception as exc:
        console.print(f"[red]Import failed:[/red] {exc}")
        raise typer.Exit(code=1)


@design_app.command("sketch-export")
def design_sketch_export(
    svg: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="SVG file to export."),
    document: Path = typer.Option(..., "--document", help="Sketch .sketch document path."),
) -> None:
    """Export an SVG into a Sketch document."""
    plugin = SketchPlugin()
    success = plugin.export_to_sketch(svg, document)
    if success:
        console.print(f"[green]Exported[/green] {svg.name} to {document}")
    else:
        console.print(f"[red]Export failed.[/red]")
        raise typer.Exit(code=1)


@design_app.command("tokens-extract")
def design_tokens_extract(
    svg: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="SVG file to analyse."),
    output: Path = typer.Option(None, "--output", "-o", help="Output JSON path."),
) -> None:
    """Extract design tokens from an SVG."""
    sync = DesignTokenSync()
    tokens = sync.extract_tokens(svg)
    if output:
        sync.export_tokens_json(tokens, output)
        console.print(f"[green]Tokens saved[/green] {output}")
    else:
        table = Table(title=f"Design Tokens: {svg.name}")
        table.add_column("Category", style="bold")
        table.add_column("Count")
        table.add_column("Values")
        table.add_row("Colors", str(len(tokens["colors"])), ", ".join(tokens["colors"][:5]) or "-")
        table.add_row("Fonts", str(len(tokens["fonts"])), ", ".join(tokens["fonts"][:5]) or "-")
        table.add_row("Spacing", str(len(tokens["spacing"])), ", ".join(tokens["spacing"][:5]) or "-")
        console.print(table)


# ------------------------------------------------------------------
# 3D sub-commands
# ------------------------------------------------------------------

@three_d_app.command("extrude")
def three_d_extrude(
    svg: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="SVG file to extrude."),
    depth: float = typer.Option(10.0, "--depth", help="Extrusion depth."),
    output: Path = typer.Option(None, "--output", "-o", help="Output SVG path."),
) -> None:
    """Apply a 3-D extrusion effect to an SVG."""
    engine = SVG3D()
    result = engine.extrude(svg, depth=depth)
    out = output or svg.with_stem(svg.stem + "_extruded")
    if out.suffix.lower() != ".svg":
        out = out.with_suffix(".svg")
    out.write_text(result, encoding="utf-8")
    console.print(f"[green]Extruded SVG[/green] {out}")


@three_d_app.command("rotate")
def three_d_rotate(
    svg: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="SVG file to rotate."),
    axis: str = typer.Option("z", "--axis", help="Rotation axis: x, y, z."),
    angle: float = typer.Option(45.0, "--angle", help="Rotation angle in degrees."),
    output: Path = typer.Option(None, "--output", "-o", help="Output SVG path."),
) -> None:
    """Apply a 3-D rotation to an SVG."""
    engine = SVG3D()
    result = engine.rotate(svg, axis=axis, angle=angle)
    out = output or svg.with_stem(svg.stem + f"_rotate_{axis}_{angle}")
    if out.suffix.lower() != ".svg":
        out = out.with_suffix(".svg")
    out.write_text(result, encoding="utf-8")
    console.print(f"[green]Rotated SVG[/green] {out}")


@three_d_app.command("ar-preview")
def three_d_ar_preview(
    svg: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="SVG file for AR preview."),
    width: float = typer.Option(100.0, "--width", help="Physical width in mm."),
    output: Path = typer.Option(None, "--output", "-o", help="Output USDZ path."),
) -> None:
    """Generate an AR preview package from an SVG."""
    ar = ARPreview()
    usdz_path = output or svg.with_suffix(".usdz")
    try:
        ar.export_usdz(svg, usdz_path)
        console.print(f"[green]AR preview[/green] {usdz_path}")
    except Exception as exc:
        console.print(f"[red]AR export failed:[/red] {exc}")
        raise typer.Exit(code=1)


# ------------------------------------------------------------------
# Enterprise sub-commands
# ------------------------------------------------------------------

@enterprise_app.command("team")
def enterprise_team(
    action: str = typer.Argument(..., help="Action: create, add-member, remove-member, list."),
    name: str = typer.Argument("", help="Workspace name or user ID."),
    role: str = typer.Option("editor", "--role", "-r", help="Role: admin, editor, viewer, guest."),
) -> None:
    """Manage enterprise team workspaces."""
    if action == "create":
        if not name:
            console.print("[red]Workspace name is required.[/red]")
            raise typer.Exit(code=1)
        ws = TeamWorkspace(name=name, owner="cli_user")
        ws_dir = Path.home() / ".bitmap_vector_studio" / "workspaces"
        ws_dir.mkdir(parents=True, exist_ok=True)
        ws_file = ws_dir / f"{ws.workspace_id}.json"
        ws_file.write_text(json.dumps(ws.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        console.print(f"[green]Created workspace[/green] {ws.workspace_id} ({name})")
        return

    if action == "add-member":
        if not name:
            console.print("[red]User ID is required.[/red]")
            raise typer.Exit(code=1)
        ws_dir = Path.home() / ".bitmap_vector_studio" / "workspaces"
        ws_files = sorted(ws_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True) if ws_dir.exists() else []
        if not ws_files:
            console.print("[red]No workspace found. Create one first with 'enterprise team create <name>'.[/red]")
            raise typer.Exit(code=1)
        ws_data = json.loads(ws_files[0].read_text(encoding="utf-8"))
        ws = TeamWorkspace.from_dict(ws_data)
        if ws.add_member(name, role):
            ws_files[0].write_text(json.dumps(ws.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
            console.print(f"[green]Added member[/green] {name} as {role}")
        else:
            console.print(f"[yellow]Failed to add member[/yellow] {name}")
        return

    if action == "list":
        ws_dir = Path.home() / ".bitmap_vector_studio" / "workspaces"
        if not ws_dir.exists():
            console.print("[yellow]No workspaces found.[/yellow]")
            return
        table = Table(title="Team Workspaces")
        table.add_column("ID", style="bold")
        table.add_column("Name")
        table.add_column("Owner")
        table.add_column("Members")
        for ws_file in ws_dir.glob("*.json"):
            try:
                data = json.loads(ws_file.read_text(encoding="utf-8"))
                table.add_row(
                    data.get("workspace_id", "-"),
                    data.get("name", "-"),
                    data.get("owner", "-"),
                    str(len(data.get("members", {}))),
                )
            except Exception:
                continue
        console.print(table)
        return

    console.print(f"[red]Unknown action:[/red] {action}")
    raise typer.Exit(code=1)


@enterprise_app.command("audit-log")
def enterprise_audit_log(
    workspace_id: str = typer.Argument("", help="Workspace ID to inspect."),
) -> None:
    """Show the audit log for a workspace."""
    ws_dir = Path.home() / ".bitmap_vector_studio" / "workspaces"
    target: Path | None = None
    if workspace_id:
        target = ws_dir / f"{workspace_id}.json"
    else:
        files = sorted(ws_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True) if ws_dir.exists() else []
        if files:
            target = files[0]
    if target is None or not target.exists():
        console.print("[yellow]No workspace found.[/yellow]")
        return
    data = json.loads(target.read_text(encoding="utf-8"))
    ws = TeamWorkspace.from_dict(data)
    log = ws.get_audit_log()
    if not log:
        console.print("[yellow]No audit log entries.[/yellow]")
        return
    table = Table(title="Audit Log")
    table.add_column("Time", style="bold")
    table.add_column("User")
    table.add_column("Action")
    table.add_column("Resource")
    for entry in log:
        table.add_row(
            entry.get("timestamp", "-"),
            entry.get("user_id", "-"),
            entry.get("action", "-"),
            entry.get("resource", "-"),
        )
    console.print(table)


@enterprise_app.command("sso-configure")
def enterprise_sso_configure(
    provider: str = typer.Option(..., "--provider", "-p", help="SSO provider: google, github, saml, ldap."),
    client_id: str = typer.Option("", "--client-id", help="Client / application ID."),
    redirect_url: str = typer.Option("http://localhost:8000/callback", "--redirect-url", help="Redirect URL."),
) -> None:
    """Configure an SSO provider."""
    sso = SSOIntegration()
    config: dict[str, str] = {"redirect_url": redirect_url}
    if client_id:
        config["client_id"] = client_id
    if sso.configure_sso(provider, config):
        sso_dir = Path.home() / ".bitmap_vector_studio" / "sso"
        sso_dir.mkdir(parents=True, exist_ok=True)
        sso_file = sso_dir / f"{provider}.json"
        sso_file.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
        console.print(f"[green]Configured SSO[/green] {provider}")
    else:
        console.print(f"[red]Failed to configure SSO[/red] {provider}")
        raise typer.Exit(code=1)


# ------------------------------------------------------------------
# Template market sub-commands
# ------------------------------------------------------------------

@template_app.command("list")
def template_list(
    category: str | None = typer.Option(None, "--category", "-c", help="Filter by category."),
    query: str | None = typer.Option(None, "--query", "-q", help="Search query."),
) -> None:
    """List available templates from the marketplace."""
    market = TemplateMarket()
    templates = market.discover_templates(query=query, category=category)
    if not templates:
        console.print("[yellow]No templates found.[/yellow]")
        return
    table = Table(title="Templates")
    table.add_column("ID", style="bold")
    table.add_column("Name")
    table.add_column("Category")
    table.add_column("Author")
    table.add_column("Rating")
    table.add_column("Downloads")
    for t in templates:
        table.add_row(
            t.template_id,
            t.name,
            t.category,
            t.author or "-",
            f"{t.rating:.1f}",
            str(t.downloads),
        )
    console.print(table)


@template_app.command("recommend")
def template_recommend(
    user_id: str = typer.Option("cli_user", "--user", "-u", help="User identifier."),
    image_type: str = typer.Option("logo", "--image-type", help="Context image type."),
) -> None:
    """Get AI-powered template recommendations."""
    market = TemplateMarket()
    recs = market.get_recommendations(user_id, {"image_type": image_type})
    if not recs:
        console.print("[yellow]No recommendations available.[/yellow]")
        return
    table = Table(title=f"Recommendations for {user_id}")
    table.add_column("ID", style="bold")
    table.add_column("Name")
    table.add_column("Category")
    table.add_column("Rating")
    for t in recs:
        table.add_row(t.template_id, t.name, t.category, f"{t.rating:.1f}")
    console.print(table)


@template_app.command("apply")
def template_apply(
    template_id: str = typer.Argument(..., help="Template ID to apply."),
    input_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Input bitmap image."),
    output: Path = typer.Option(..., "--output", "-o", help="Output SVG path."),
) -> None:
    """Apply a template to an input image."""
    market = TemplateMarket()
    try:
        result_path = market.apply_template(template_id, input_path, output)
        console.print(f"[green]Applied template[/green] {template_id} → {result_path}")
    except Exception as exc:
        console.print(f"[red]Failed to apply template:[/red] {exc}")
        raise typer.Exit(code=1)


@template_app.command("batch-apply")
def template_batch_apply(
    template_id: str = typer.Argument(..., help="Template ID to apply."),
    input_dir: Path = typer.Argument(..., exists=True, file_okay=False, readable=True, help="Input images directory."),
    output_dir: Path = typer.Argument(..., help="Output directory."),
    workers: int = typer.Option(4, "--workers", "-w", min=1, max=16, help="Concurrent workers."),
) -> None:
    """Batch-apply a template to all images in a directory."""
    from .batch_template import BatchTemplateApplier

    applier = BatchTemplateApplier(max_workers=workers)
    try:
        results = applier.apply_to_directory(
            template_id,
            input_dir,
            output_dir,
            on_progress=lambda current, total, filename: console.print(
                f"  [{current}/{total}] {filename} ...", end=" \r"
            ),
        )
        console.print(f"\n[green]Batch apply completed:[/green] {len(results)} file(s)")
        for p in results:
            console.print(f"  → {p}")
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)
    except Exception as exc:
        console.print(f"[red]Batch apply failed:[/red] {exc}")
        raise typer.Exit(code=1)


@template_app.command("publish")
def template_publish(
    file: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Template JSON file to publish."),
    user_id: str = typer.Option("cli_user", "--user", "-u", help="Publisher user identifier."),
) -> None:
    """Publish a template JSON file to the marketplace."""
    editor = TemplateEditor()
    try:
        data = editor.load_template(file)
    except Exception as exc:
        console.print(f"[red]Invalid template file:[/red] {exc}")
        raise typer.Exit(code=1)
    template = Template.from_dict(data)
    market = TemplateMarket()
    tid = market.publish_template(template, user_id)
    console.print(f"[green]Published template[/green] {tid}")


# ------------------------------------------------------------------
# Cache sub-commands
# ------------------------------------------------------------------

@cache_app.command("status")
def cache_status() -> None:
    """Show cache status and statistics."""
    mgr = CacheManager()
    stats = mgr.stats()
    table = Table(title="Cache Status")
    table.add_column("Property", style="bold")
    table.add_column("Value")
    table.add_row("Cache directory", stats["cache_dir"])
    table.add_row("Memory entries", str(stats["memory_entries"]))
    table.add_row("Disk entries", str(stats["disk_entries"]))
    table.add_row("Disk size (MB)", str(stats["disk_size_mb"]))
    table.add_row("Disk max size (MB)", str(stats["disk_max_size_mb"]))
    console.print(table)


@cache_app.command("clear")
def cache_clear(
    level: str = typer.Option("all", "--level", "-l", help="Cache level to clear: memory, disk, all."),
) -> None:
    """Clear cache at the specified level."""
    mgr = CacheManager()
    if level not in ("memory", "disk", "all"):
        console.print(f"[red]Invalid level:[/red] {level}. Choose from memory, disk, all.")
        raise typer.Exit(code=1)
    mgr.clear(level=level)
    console.print(f"[green]Cleared[/green] {level} cache")


# ------------------------------------------------------------------
# Render farm sub-commands
# ------------------------------------------------------------------

@farm_app.command("status")
def farm_status(
    api_url: str = typer.Option("http://localhost:8000", "--api-url", help="Base URL of the API server."),
) -> None:
    """Show the current status of the render farm."""
    import urllib.request
    import urllib.error
    import json as _json

    url = f"{api_url}/farm/status"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        console.print(f"[red]API error:[/red] {exc.code} {exc.reason}")
        raise typer.Exit(code=1)
    except Exception as exc:
        console.print(f"[red]Failed to fetch farm status:[/red] {exc}")
        raise typer.Exit(code=1)

    summary = data.get("summary", {})
    table = Table(title="Render Farm Status")
    table.add_column("Property", style="bold")
    table.add_column("Value")
    table.add_row("Total workers", str(summary.get("total_workers", 0)))
    table.add_row("Alive workers", str(summary.get("alive_workers", 0)))
    table.add_row("Total tasks", str(summary.get("total_tasks", 0)))
    table.add_row("Pending", str(summary.get("pending", 0)))
    table.add_row("Running", str(summary.get("running", 0)))
    table.add_row("Completed", str(summary.get("completed", 0)))
    table.add_row("Failed", str(summary.get("failed", 0)))
    console.print(table)

    workers = data.get("workers", [])
    if workers:
        wtable = Table(title="Workers")
        wtable.add_column("ID", style="bold")
        wtable.add_column("Host")
        wtable.add_column("Port")
        wtable.add_column("Load")
        wtable.add_column("Capacity")
        wtable.add_column("Alive")
        for w in workers:
            wtable.add_row(
                w.get("worker_id", "-"),
                w.get("host", "-"),
                str(w.get("port", "-")),
                str(w.get("current_load", "-")),
                str(w.get("capacity", "-")),
                "yes" if w.get("alive") else "no",
            )
        console.print(wtable)


@farm_app.command("submit")
def farm_submit(
    file: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Input bitmap image."),
    api_url: str = typer.Option("http://localhost:8000", "--api-url", help="Base URL of the API server."),
    preset: str = typer.Option("poster", "--preset", "-p", help="Preset to use."),
    priority: int = typer.Option(0, "--priority", min=0, max=100, help="Task priority."),
) -> None:
    """Submit a single image to the render farm."""
    import urllib.request
    import urllib.error
    import json as _json
    import mimetypes

    url = f"{api_url}/farm/submit"
    content_type, _ = mimetypes.guess_type(str(file))
    content_type = content_type or "application/octet-stream"
    boundary = f"----vs-farm-{uuid.uuid4().hex}"

    def _encode_multipart() -> bytes:
        lines: list[bytes] = []
        lines.append(f"--{boundary}".encode("utf-8"))
        lines.append(f'Content-Disposition: form-data; name="file"; filename="{file.name}"'.encode("utf-8"))
        lines.append(f"Content-Type: {content_type}".encode("utf-8"))
        lines.append(b"")
        lines.append(file.read_bytes())
        lines.append(f"--{boundary}".encode("utf-8"))
        lines.append(b'Content-Disposition: form-data; name="preset"')
        lines.append(b"")
        lines.append(preset.encode("utf-8"))
        lines.append(f"--{boundary}".encode("utf-8"))
        lines.append(b'Content-Disposition: form-data; name="priority"')
        lines.append(b"")
        lines.append(str(priority).encode("utf-8"))
        lines.append(f"--{boundary}--".encode("utf-8"))
        return b"\r\n".join(lines)

    body = _encode_multipart()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        console.print(f"[red]API error:[/red] {exc.code} {exc.reason}")
        raise typer.Exit(code=1)
    except Exception as exc:
        console.print(f"[red]Submit failed:[/red] {exc}")
        raise typer.Exit(code=1)

    console.print(f"[green]Submitted[/green] task {data['task_id']} (status: {data['status']})")


@farm_app.command("batch")
def farm_batch(
    input_dir: Path = typer.Argument(..., exists=True, file_okay=False, readable=True, help="Input folder."),
    output_dir: Path = typer.Option(..., "--output-dir", "-o", help="Output directory."),
    api_url: str = typer.Option("http://localhost:8000", "--api-url", help="Base URL of the API server."),
    preset: str = typer.Option("poster", "--preset", "-p", help="Preset to use."),
    chunk_size: int = typer.Option(4, "--chunk-size", "-c", min=1, max=64, help="Files per chunk."),
) -> None:
    """Batch-submit a folder of images to the render farm."""
    from .render_farm import DistributedBatch

    output_dir.mkdir(parents=True, exist_ok=True)
    chunks = DistributedBatch.split_batch(input_dir, chunk_size)
    if not chunks:
        console.print("[yellow]No supported images found.[/yellow]")
        raise typer.Exit(code=0)

    console.print(f"Split {sum(len(c) for c in chunks)} image(s) into {len(chunks)} chunk(s)")

    # Register local workers via API (for this CLI we just submit directly to farm API).
    import urllib.request
    import urllib.error
    import json as _json
    import mimetypes

    task_ids: list[str] = []
    for chunk in chunks:
        for image_path in chunk:
            url = f"{api_url}/farm/submit"
            content_type, _ = mimetypes.guess_type(str(image_path))
            content_type = content_type or "application/octet-stream"
            boundary = f"----vs-farm-{uuid.uuid4().hex}"

            def _encode_multipart(path: Path, bnd: str) -> bytes:
                lines: list[bytes] = []
                lines.append(f"--{bnd}".encode("utf-8"))
                lines.append(f'Content-Disposition: form-data; name="file"; filename="{path.name}"'.encode("utf-8"))
                lines.append(f"Content-Type: {content_type}".encode("utf-8"))
                lines.append(b"")
                lines.append(path.read_bytes())
                lines.append(f"--{bnd}".encode("utf-8"))
                lines.append(b'Content-Disposition: form-data; name="preset"')
                lines.append(b"")
                lines.append(preset.encode("utf-8"))
                lines.append(f"--{bnd}--".encode("utf-8"))
                return b"\r\n".join(lines)

            body = _encode_multipart(image_path, boundary)
            req = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = _json.loads(resp.read().decode("utf-8"))
                    task_ids.append(data["task_id"])
            except urllib.error.HTTPError as exc:
                console.print(f"[red]API error for {image_path.name}:[/red] {exc.code} {exc.reason}")
            except Exception as exc:
                console.print(f"[red]Submit failed for {image_path.name}:[/red] {exc}")

    console.print(f"[green]Submitted[/green] {len(task_ids)} task(s)")


@farm_app.command("worker")
def farm_worker(
    host: str = typer.Option("0.0.0.0", "--host", help="Bind host."),
    port: int = typer.Option(9000, "--port", help="Bind port."),
    capacity: int = typer.Option(4, "--capacity", "-c", min=1, max=16, help="Max concurrent tasks."),
    coordinator: str = typer.Option("http://localhost:8000", "--coordinator", help="Farm coordinator API URL."),
) -> None:
    """Start a local render-farm worker node."""
    from .render_farm import start_worker_server, WorkerNode
    import urllib.request
    import urllib.error
    import json as _json

    server = start_worker_server(host, port, capacity)
    worker = server._worker

    # Register with coordinator
    reg_url = f"{coordinator}/farm/workers/register"
    payload = _json.dumps({
        "worker_id": worker.worker_id,
        "host": worker.host,
        "port": worker.port,
        "capacity": worker.capacity,
    }).encode("utf-8")
    req = urllib.request.Request(
        reg_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            reg_data = _json.loads(resp.read().decode("utf-8"))
            if reg_data.get("success"):
                console.print(f"[green]Registered worker[/green] {worker.worker_id} with coordinator")
            else:
                console.print(f"[yellow]Worker already registered[/yellow] {worker.worker_id}")
    except Exception as exc:
        console.print(f"[yellow]Could not register with coordinator:[/yellow] {exc}")

    console.print(f"[green]Worker listening[/green] on http://{host}:{port}")
    console.print(f"Capacity: {capacity} | ID: {worker.worker_id}")
    console.print("Press Ctrl+C to stop.")

    # Start heartbeat thread
    def _heartbeat_loop() -> None:
        while True:
            try:
                hb_url = f"{coordinator}/farm/workers/{urllib.parse.quote(worker.worker_id)}/heartbeat"
                hb_req = urllib.request.Request(hb_url, method="POST")
                with urllib.request.urlopen(hb_req, timeout=5):
                    pass
            except Exception:
                pass
            time.sleep(10)

    hb_thread = threading.Thread(target=_heartbeat_loop, daemon=True)
    hb_thread.start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        console.print("[yellow]Shutting down worker...[/yellow]")
    finally:
        server.shutdown_server()


# ------------------------------------------------------------------
# Report sub-commands
# ------------------------------------------------------------------

@report_app.command("convert")
def report_convert(
    input_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="输入位图图片。"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="输出路径。"),
    preset: Optional[str] = typer.Option(None, "--preset", "-p", help="预设名称，不指定则自动推荐。"),
    format: str = typer.Option("json", "--format", "-f", help="报告格式: json/md/csv。"),
    optimize: str = typer.Option("basic", "--optimize", help="优化级别。"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="静默模式。"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="详细输出。"),
    config_path: Optional[Path] = typer.Option(None, "--config", help="配置文件路径。"),
    plugin: list[str] = typer.Option([], "--plugin", help="启用的插件名称。"),
) -> None:
    """转换单张图片并生成报告。"""
    from .svg_optimizer import svg_quality_score
    from .svg_tools import svg_stats

    result = _run_single_convert(
        input_path=input_path,
        output=output,
        preset=preset,
        format="svg",
        optimize_level=optimize,
        quiet=quiet,
        verbose=verbose,
        config_path=config_path,
        plugin=plugin,
    )

    input_size = input_path.stat().st_size
    output_size = result.svg_path.stat().st_size if result.svg_path.exists() else 0
    compression = input_size / output_size if output_size > 0 else 0.0

    quality = None
    paths = None
    colors = None
    try:
        qs = svg_quality_score(result.svg_path)
        quality = qs.get("overall")
    except Exception:
        pass
    try:
        st = svg_stats(result.svg_path)
        paths = st.get("paths")
        colors = st.get("colors")
    except Exception:
        pass

    report = ConversionReport(
        input_file=str(input_path),
        output_file=str(result.svg_path),
        input_size_bytes=input_size,
        output_size_bytes=output_size,
        compression_ratio=compression,
        preset_used=result.engine,
        parameters=result.stats or {},
        quality_score=quality,
        path_count=paths,
        color_count=colors,
        duration_seconds=result.elapsed_seconds,
        timestamp=datetime.now().isoformat(),
    )

    gen = ReportGenerator()
    path = gen.save_report(report, format=format)
    console.print(f"[green]报告已保存[/green] {path}")


@report_app.command("batch")
def report_batch(
    input_dir: Path = typer.Argument(..., exists=True, file_okay=False, readable=True, help="输入文件夹。"),
    output_dir: Path = typer.Argument(..., help="输出文件夹。"),
    preset: str = typer.Option("poster", "--preset", "-p", help="预设名称。"),
    format: str = typer.Option("json", "--format", "-f", help="报告格式: json/md/csv。"),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="递归扫描输入文件夹。"),
    overwrite: bool = typer.Option(False, "--overwrite", help="覆盖现有文件。"),
    optimize: str = typer.Option("basic", "--optimize", help="优化级别。"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="静默模式。"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="详细输出。"),
    workers: int = typer.Option(1, "--workers", "-w", min=1, max=16, help="并发工作数。"),
    config_path: Optional[Path] = typer.Option(None, "--config", help="配置文件路径。"),
    plugin: list[str] = typer.Option([], "--plugin", help="启用的插件名称。"),
) -> None:
    """批量转换文件夹中的图片并生成报告。"""
    from .svg_optimizer import svg_quality_score
    from .svg_tools import svg_stats

    config = _load_config(config_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    opts = options_from_preset(preset)
    iterator = input_dir.rglob("*") if recursive else input_dir.glob("*")
    images = [path for path in iterator if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS]

    if not images:
        if not quiet:
            console.print("[yellow]未找到支持的图片。[/yellow]")
        raise typer.Exit(code=0)

    plugins = _active_plugins(config, plugin)

    if not quiet:
        if verbose:
            console.print(f"[批量] 发现 {len(images)} 张图片，使用 {workers} 个工作线程")
        else:
            console.print(f"批量转换: {len(images)} 张图片")

    items: list[ConversionReport] = []
    failures = 0
    total_input = 0
    total_output = 0
    total_duration = 0.0

    for idx, image_path in enumerate(images, start=1):
        rel = image_path.relative_to(input_dir) if recursive else Path(image_path.name)
        out_path = (output_dir / rel).with_suffix(".svg")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if out_path.exists() and not overwrite:
            if verbose:
                console.print(f"[跳过] {out_path} (已存在)")
            continue
        try:
            if not quiet and not verbose:
                console.print(f"  [{idx}/{len(images)}] {image_path.name} ...", end=" ")
            result = trace_image(
                image_path,
                out_path,
                opts,
                optimize_level=optimize,
                plugins=plugins,
            )
            if not quiet:
                if verbose:
                    console.print(f"[完成] {result.svg_path}")
                else:
                    console.print("✓")

            input_size = image_path.stat().st_size
            output_size = result.svg_path.stat().st_size if result.svg_path.exists() else 0
            total_input += input_size
            total_output += output_size
            total_duration += result.elapsed_seconds

            quality = None
            paths = None
            colors = None
            try:
                qs = svg_quality_score(result.svg_path)
                quality = qs.get("overall")
            except Exception:
                pass
            try:
                st = svg_stats(result.svg_path)
                paths = st.get("paths")
                colors = st.get("colors")
            except Exception:
                pass

            items.append(
                ConversionReport(
                    input_file=str(image_path),
                    output_file=str(result.svg_path),
                    input_size_bytes=input_size,
                    output_size_bytes=output_size,
                    compression_ratio=input_size / output_size if output_size > 0 else 0.0,
                    preset_used=preset,
                    parameters=result.stats or {},
                    quality_score=quality,
                    path_count=paths,
                    color_count=colors,
                    duration_seconds=result.elapsed_seconds,
                    timestamp=datetime.now().isoformat(),
                )
            )
        except Exception as exc:
            failures += 1
            total_input += image_path.stat().st_size
            items.append(
                ConversionReport(
                    input_file=str(image_path),
                    output_file="",
                    input_size_bytes=image_path.stat().st_size,
                    output_size_bytes=0,
                    compression_ratio=0.0,
                    preset_used=preset,
                    parameters={},
                    quality_score=None,
                    path_count=None,
                    color_count=None,
                    duration_seconds=0.0,
                    timestamp=datetime.now().isoformat(),
                )
            )
            if not quiet:
                if verbose:
                    console.print(f"[失败] {image_path}: {exc}")
                else:
                    console.print(f"✗ ({exc})")

    batch_report = BatchReport(
        total_files=len(images),
        successful=len(items) - failures,
        failed=failures,
        total_input_size=total_input,
        total_output_size=total_output,
        average_duration=total_duration / len(items) if items else 0.0,
        preset_used=preset,
        items=items,
        timestamp=datetime.now().isoformat(),
    )

    gen = ReportGenerator()
    path = gen.save_report(batch_report, format=format)
    console.print(f"[green]批量报告已保存[/green] {path}")
    if failures:
        console.print(f"[red]失败 {failures}/{len(images)}[/red]")
        raise typer.Exit(code=1)
    if not quiet:
        console.print(f"[green]完成 {len(images)} 张图片转换[/green]")


@report_app.command("list")
def report_list() -> None:
    """列出所有历史报告。"""
    gen = ReportGenerator()
    reports = gen.list_reports()
    if not reports:
        console.print("[yellow]暂无报告。[/yellow]")
        return

    table = Table(title="历史报告")
    table.add_column("#", style="bold")
    table.add_column("文件名")
    table.add_column("格式")
    table.add_column("修改时间")
    for idx, r in enumerate(reports, start=1):
        suffix = r.suffix.lstrip(".")
        mtime = datetime.fromtimestamp(r.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        table.add_row(str(idx), r.name, suffix, mtime)
    console.print(table)


# ------------------------------------------------------------------
# Stats command
# ------------------------------------------------------------------

@app.command("stats")
def stats_command(
    days: int = typer.Option(30, "--days", "-d", min=1, max=365, help="统计天数。"),
) -> None:
    """显示统计仪表盘。"""
    dashboard = StatsDashboard()
    summary = dashboard.get_summary(days=days)
    trend = dashboard.get_daily_trend(days=min(days, 14))

    table = Table(title=f"统计仪表盘 (最近 {days} 天)")
    table.add_column("指标", style="bold")
    table.add_column("数值")
    table.add_row("总转换数", str(summary["total_conversions"]))
    table.add_row("成功", str(summary["successful"]))
    table.add_row("失败", str(summary["failed"]))
    table.add_row("成功率", f"{summary['success_rate']:.1f}%")
    table.add_row("平均耗时", f"{summary['average_duration']:.2f}s")
    console.print(table)

    if summary["top_presets"]:
        ptable = Table(title="常用预设")
        ptable.add_column("预设", style="bold")
        ptable.add_column("使用次数")
        for preset_name, count in summary["top_presets"]:
            ptable.add_row(preset_name, str(count))
        console.print(ptable)

    if trend:
        ttable = Table(title="每日趋势 (最近14天)")
        ttable.add_column("日期", style="bold")
        ttable.add_column("转换数")
        for day in trend:
            ttable.add_row(day["date"], str(day["count"]))
        console.print(ttable)


# ------------------------------------------------------------------
# Health / Metrics / Status commands
# ------------------------------------------------------------------

@app.command("health")
def health_command() -> None:
    """显示系统健康状态."""
    from .health_check import HealthChecker, check_disk_space, check_memory, check_python_deps, check_vtracer

    checker = HealthChecker()
    checker.register("disk", lambda: check_disk_space())
    checker.register("memory", lambda: check_memory())
    checker.register("deps", lambda: check_python_deps())
    checker.register("vtracer", lambda: check_vtracer())

    status = checker.check()
    table = Table(title=f"Health Status — {status.status.upper()}")
    table.add_column("Check", style="bold")
    table.add_column("Status")
    table.add_column("Details")

    for name, result in status.checks.items():
        if result["status"] == "pass":
            status_str = "[green]✓[/green]"
            details = str(result.get("details", ""))
        else:
            status_str = "[red]✗[/red]"
            details = result.get("error", "unknown error")
        table.add_row(name, status_str, details)

    console.print(table)
    console.print(f"Version: {status.version} | Uptime: {status.uptime_seconds:.1f}s")
    if status.status != "healthy":
        raise typer.Exit(code=1)


@app.command("metrics")
def metrics_command() -> None:
    """显示性能指标."""
    from .metrics import get_metrics

    snapshot = get_metrics().get_snapshot()
    conv = snapshot["conversion"]
    table = Table(title="Performance Metrics")
    table.add_column("Metric", style="bold")
    table.add_column("Value")

    table.add_row("Total conversions", str(conv["total"]))
    table.add_row("Successful", str(conv["successful"]))
    table.add_row("Failed", str(conv["failed"]))
    table.add_row("Success rate", f"{conv['success_rate']}%")
    table.add_row("Average duration", f"{conv['average_duration']}s")
    table.add_row("P95 duration", f"{conv['p95_duration']}s")
    table.add_row("Queue length", str(snapshot["queue"]["length"]))
    table.add_row("Active workers", str(snapshot["workers"]["active"]))

    console.print(table)


@app.command("status")
def status_command() -> None:
    """综合状态报告（健康 + 指标 + 版本）."""
    from .health_check import HealthChecker, check_disk_space, check_memory, check_python_deps, check_vtracer
    from .metrics import get_metrics

    checker = HealthChecker()
    checker.register("disk", lambda: check_disk_space())
    checker.register("memory", lambda: check_memory())
    checker.register("deps", lambda: check_python_deps())
    checker.register("vtracer", lambda: check_vtracer())

    health = checker.check()
    metrics = get_metrics().get_snapshot()

    table = Table(title=f"System Status — {health.status.upper()}")
    table.add_column("Component", style="bold")
    table.add_column("State")

    table.add_row("Health", health.status)
    table.add_row("Version", health.version)
    table.add_row("Uptime", f"{health.uptime_seconds:.1f}s")
    table.add_row("Conversions", str(metrics["conversion"]["total"]))
    table.add_row("Success rate", f"{metrics['conversion']['success_rate']}%")
    table.add_row("Queue", str(metrics["queue"]["length"]))
    table.add_row("Workers", str(metrics["workers"]["active"]))

    for name, result in health.checks.items():
        icon = "✓" if result["status"] == "pass" else "✗"
        table.add_row(f"Check: {name}", icon)

    console.print(table)
    if health.status != "healthy":
        raise typer.Exit(code=1)


# ------------------------------------------------------------------
# Security commands
# ------------------------------------------------------------------

@security_app.command("scan")
def security_scan(
    file: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="File to scan."),
) -> None:
    """Scan a file for security issues."""
    try:
        path = InputValidator.validate_file_path(file)
        InputValidator.validate_image_file(path)
        file_hash = FileHashChecker.compute_hash(path)
        console.print(f"[green]File is safe:[/green] {path}")
        console.print(f"SHA256: {file_hash}")
    except SecurityError as exc:
        console.print(f"[red]Security check failed:[/red] {exc}")
        raise typer.Exit(code=1)


@security_app.command("sanitize")
def security_sanitize(
    svg: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="SVG file to sanitize."),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output path for sanitized SVG."),
) -> None:
    """Sanitize an SVG file by removing dangerous elements."""
    svg_content = svg.read_text(encoding="utf-8")
    if SVGSanitizer.is_safe(svg_content):
        console.print(f"[green]SVG is already safe:[/green] {svg}")
        return
    clean_svg = SVGSanitizer.sanitize(svg_content)
    out = output or svg.with_suffix(".sanitized.svg")
    out.write_text(clean_svg, encoding="utf-8")
    console.print(f"[green]Sanitized SVG saved to:[/green] {out}")


# ------------------------------------------------------------------
# Audit commands
# ------------------------------------------------------------------

@audit_app.command("log")
def audit_log(
    user: str | None = typer.Option(None, "--user", "-u", help="Filter by user."),
    action: str | None = typer.Option(None, "--action", "-a", help="Filter by action."),
    limit: int = typer.Option(50, "--limit", "-l", min=1, max=500, help="Maximum number of entries."),
) -> None:
    """View audit logs."""
    logger = AuditLogger()
    events = logger.query(user=user, action=action, limit=limit)
    if not events:
        console.print("[yellow]No audit events found.[/yellow]")
        return

    table = Table(title="Audit Log")
    table.add_column("Timestamp", style="bold")
    table.add_column("Level")
    table.add_column("Action")
    table.add_column("User")
    table.add_column("Resource")

    for event in events:
        level_color = {
            "security": "red",
            "error": "red",
            "warning": "yellow",
            "info": "green",
        }.get(event["level"], "white")
        table.add_row(
            event["timestamp"],
            f"[{level_color}]{event['level']}[/{level_color}]",
            event["action"],
            event["user"],
            event["resource"],
        )
    console.print(table)


# ------------------------------------------------------------------
# Notify sub-commands
# ------------------------------------------------------------------

@notify_app.command("add-webhook")
def notify_add_webhook(
    url: str = typer.Argument(..., help="Webhook URL."),
    events: list[str] = typer.Option([], "--event", help="Event types to subscribe (can be used multiple times)."),
) -> None:
    """Add a Webhook notification."""
    notifier = Notifier()
    notifier.add_webhook(url, events=events or None)
    console.print(f"[green]Added webhook:[/green] {url}")


@notify_app.command("add-slack")
def notify_add_slack(
    url: str = typer.Argument(..., help="Slack webhook URL."),
    events: list[str] = typer.Option([], "--event", help="Event types to subscribe (can be used multiple times)."),
) -> None:
    """Add a Slack notification."""
    notifier = Notifier()
    notifier.add_slack(url, events=events or None)
    console.print(f"[green]Added Slack webhook:[/green] {url}")


@notify_app.command("add-discord")
def notify_add_discord(
    url: str = typer.Argument(..., help="Discord webhook URL."),
    events: list[str] = typer.Option([], "--event", help="Event types to subscribe (can be used multiple times)."),
) -> None:
    """Add a Discord notification."""
    notifier = Notifier()
    notifier.add_discord(url, events=events or None)
    console.print(f"[green]Added Discord webhook:[/green] {url}")


@notify_app.command("list")
def notify_list() -> None:
    """List all notification configurations."""
    notifier = Notifier()
    configs = notifier.list()
    if not configs:
        console.print("[yellow]No notifications configured.[/yellow]")
        return

    table = Table(title="Notification Configurations")
    table.add_column("#", style="bold")
    table.add_column("Channel")
    table.add_column("URL")
    table.add_column("Enabled")
    table.add_column("Events")

    for idx, cfg in enumerate(configs, start=1):
        table.add_row(
            str(idx),
            cfg.channel.value,
            cfg.url or "-",
            "yes" if cfg.enabled else "no",
            ", ".join(cfg.events or notifier.EVENTS),
        )
    console.print(table)


@notify_app.command("remove")
def notify_remove(
    index: int = typer.Argument(..., min=0, help="Index of the notification to remove (from list)."),
) -> None:
    """Remove a notification configuration."""
    notifier = Notifier()
    if notifier.remove(index):
        console.print(f"[green]Removed notification at index {index}.[/green]")
    else:
        console.print(f"[red]Invalid index:[/red] {index}")
        raise typer.Exit(code=1)


@notify_app.command("test")
def notify_test(
    event: str = typer.Option("convert.complete", "--event", help="Event type to test."),
) -> None:
    """Test notifications by sending a sample payload."""
    notifier = Notifier()
    results = notifier.notify(
        event,
        {"file": "test.png", "preset": "poster", "duration": 1.23},
    )
    if not results:
        console.print("[yellow]No active notifications to test.[/yellow]")
        return

    table = Table(title="Test Results")
    table.add_column("Channel", style="bold")
    table.add_column("Success")
    table.add_column("Message")
    for channel, success, message in results:
        status = "[green]yes[/green]" if success else "[red]no[/red]"
        table.add_row(channel, status, message)
    console.print(table)


# ------------------------------------------------------------------
# Search sub-commands
# ------------------------------------------------------------------

@search_app.command("history")
def search_history(
    query: str = typer.Argument("", help="Search query."),
    status: str | None = typer.Option(None, "--status", help="Filter by status: completed, failed."),
    preset: str | None = typer.Option(None, "--preset", "-p", help="Filter by preset name."),
    limit: int = typer.Option(20, "--limit", "-l", min=1, max=100, help="Maximum results."),
) -> None:
    """Search conversion history."""
    engine = HistorySearch()
    results = engine.search(query, status=status, preset=preset, limit=limit)
    if not results:
        console.print("[yellow]No history records found.[/yellow]")
        return

    table = Table(title=f"History Search Results ({len(results)})")
    table.add_column("Score", style="bold")
    table.add_column("File")
    table.add_column("Preset")
    table.add_column("Status")
    table.add_column("Timestamp")
    for r in results:
        item = r.item
        table.add_row(
            f"{r.score:.1f}",
            Path(item.get("input_path", "")).name,
            item.get("preset_name", "-"),
            "completed" if item.get("output_path") else "failed",
            item.get("timestamp", "-"),
        )
    console.print(table)


@search_app.command("files")
def search_files(
    query: str = typer.Argument(..., help="Search query."),
    directory: Path = typer.Option(Path("."), "--dir", "-d", help="Directory to search."),
    limit: int = typer.Option(20, "--limit", "-l", min=1, max=100, help="Maximum results."),
) -> None:
    """Search files in a directory."""
    engine = SearchEngine()
    for path in directory.rglob("*"):
        if path.is_file():
            engine.add(
                path,
                {
                    "name": path.name,
                    "stem": path.stem,
                    "suffix": path.suffix,
                    "parent": str(path.parent),
                },
            )

    results = engine.search(query, limit=limit)
    if not results:
        console.print("[yellow]No files found.[/yellow]")
        return

    table = Table(title=f"File Search Results ({len(results)})")
    table.add_column("Score", style="bold")
    table.add_column("Path")
    table.add_column("Matched")
    for r in results:
        path = r.item
        table.add_row(
            f"{r.score:.1f}",
            str(path),
            ", ".join(r.matched_fields),
        )
    console.print(table)


# Sub-typer for import/export commands
export_app = typer.Typer(help="Export data packages.")
app.add_typer(export_app, name="export")

import_app = typer.Typer(help="Import data packages.")
app.add_typer(import_app, name="import")

# Sub-typer for tag commands
tag_app = typer.Typer(help="File tag management.")
app.add_typer(tag_app, name="tag")


# ------------------------------------------------------------------
# Export sub-commands
# ------------------------------------------------------------------

@export_app.command("json")
def export_json(
    output: Path = typer.Option(..., "--output", "-o", help="Output JSON file path."),
    presets: bool = typer.Option(True, "--presets/--no-presets", help="Include presets."),
    config: bool = typer.Option(True, "--config/--no-config", help="Include configuration."),
    history: bool = typer.Option(True, "--history/--no-history", help="Include history."),
    templates: bool = typer.Option(True, "--templates/--no-templates", help="Include templates."),
) -> None:
    """Export data to a JSON file."""
    from .import_export import ImportExporter

    include: list[str] = []
    if presets:
        include.append("presets")
    if config:
        include.append("config")
    if history:
        include.append("history")
    if templates:
        include.append("templates")

    exporter = ImportExporter()
    exporter.export_to_json(output, include=include)
    console.print(f"[green]Exported to[/green] {output}")


@export_app.command("zip")
def export_zip(
    output: Path = typer.Option(..., "--output", "-o", help="Output ZIP file path."),
    presets: bool = typer.Option(True, "--presets/--no-presets", help="Include presets."),
    config: bool = typer.Option(True, "--config/--no-config", help="Include configuration."),
    history: bool = typer.Option(True, "--history/--no-history", help="Include history."),
    templates: bool = typer.Option(True, "--templates/--no-templates", help="Include templates."),
) -> None:
    """Export data to a ZIP archive."""
    from .import_export import ImportExporter

    include: list[str] = []
    if presets:
        include.append("presets")
    if config:
        include.append("config")
    if history:
        include.append("history")
    if templates:
        include.append("templates")

    exporter = ImportExporter()
    exporter.export_to_zip(output, include=include)
    console.print(f"[green]Exported to[/green] {output}")


# ------------------------------------------------------------------
# Import sub-commands
# ------------------------------------------------------------------

@import_app.command("json")
def import_json(
    input_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Input JSON file path."),
    strategy: str = typer.Option("merge", "--strategy", help="merge / replace / skip."),
) -> None:
    """Import data from a JSON file."""
    from .import_export import ImportExporter

    if strategy not in {"merge", "replace", "skip"}:
        console.print(f"[red]Invalid strategy:[/red] {strategy}")
        raise typer.Exit(code=1)

    exporter = ImportExporter()
    stats = exporter.import_from_json(input_path, merge_strategy=strategy)
    console.print(f"[green]Import complete[/green]")
    for category, count in stats.get("imported", {}).items():
        console.print(f"  {category}: {count} items")
    for error in stats.get("errors", []):
        console.print(f"[red]Error:[/red] {error}")


@import_app.command("zip")
def import_zip(
    input_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="Input ZIP file path."),
    strategy: str = typer.Option("merge", "--strategy", help="merge / replace / skip."),
) -> None:
    """Import data from a ZIP archive."""
    from .import_export import ImportExporter

    if strategy not in {"merge", "replace", "skip"}:
        console.print(f"[red]Invalid strategy:[/red] {strategy}")
        raise typer.Exit(code=1)

    exporter = ImportExporter()
    stats = exporter.import_from_zip(input_path, merge_strategy=strategy)
    console.print(f"[green]Import complete[/green]")
    for category, count in stats.get("imported", {}).items():
        console.print(f"  {category}: {count} items")
    for error in stats.get("errors", []):
        console.print(f"[red]Error:[/red] {error}")


# ------------------------------------------------------------------
# Tag sub-commands
# ------------------------------------------------------------------

@tag_app.command("add")
def tag_add(
    file_path: str = typer.Argument(..., help="File path to tag."),
    tag: str = typer.Argument(..., help="Tag to add."),
) -> None:
    """Add a tag to a file."""
    from .tag_manager import TagManager

    manager = TagManager()
    manager.add_tag(file_path, tag)
    console.print(f"[green]Added tag[/green] '{tag}' to {file_path}")


@tag_app.command("remove")
def tag_remove(
    file_path: str = typer.Argument(..., help="File path."),
    tag: str = typer.Argument(..., help="Tag to remove."),
) -> None:
    """Remove a tag from a file."""
    from .tag_manager import TagManager

    manager = TagManager()
    manager.remove_tag(file_path, tag)
    console.print(f"[green]Removed tag[/green] '{tag}' from {file_path}")


@tag_app.command("list")
def tag_list(
    file_path: str = typer.Argument(..., help="File path to list tags for."),
) -> None:
    """List tags for a file."""
    from .tag_manager import TagManager

    manager = TagManager()
    tags = manager.get_tags(file_path)
    if not tags:
        console.print(f"[yellow]No tags for[/yellow] {file_path}")
        return
    console.print(f"Tags for {file_path}: {', '.join(tags)}")


@tag_app.command("search")
def tag_search(
    tag: str = typer.Argument(..., help="Tag to search for."),
) -> None:
    """Search files by tag."""
    from .tag_manager import TagManager

    manager = TagManager()
    results = manager.search_by_tag(tag)
    if not results:
        console.print(f"[yellow]No files found with tag[/yellow] '{tag}'")
        return
    console.print(f"Files tagged with '{tag}':")
    for path in results:
        console.print(f"  {path}")


@tag_app.command("suggest")
def tag_suggest(
    file_path: str = typer.Argument(..., help="File path."),
    preset: str | None = typer.Option(None, "--preset", "-p", help="Preset name for context."),
) -> None:
    """Suggest tags for a file."""
    from .tag_manager import TagManager

    manager = TagManager()
    suggestions = manager.suggest_tags(file_path, preset)
    if not suggestions:
        console.print("[yellow]No suggestions.[/yellow]")
        return
    console.print(f"Suggested tags: {', '.join(suggestions)}")


@tag_app.command("auto")
def tag_auto(
    file_path: str = typer.Argument(..., help="File path."),
    preset: str | None = typer.Option(None, "--preset", "-p", help="Preset name for context."),
) -> None:
    """Auto-tag a file based on its features."""
    from .tag_manager import TagManager

    manager = TagManager()
    added = manager.auto_tag(file_path, preset)
    if not added:
        console.print("[yellow]No new tags added.[/yellow]")
        return
    console.print(f"[green]Auto-tagged[/green] {file_path} with: {', '.join(added)}")


# ------------------------------------------------------------------
# Cloud storage sub-commands
# ------------------------------------------------------------------

@storage_app.command("add")
def storage_add(
    name: str = typer.Argument(..., help="Storage configuration name."),
    provider: str = typer.Option(..., "--provider", "-p", help="Provider: local, s3, oss, cos."),
    bucket: str = typer.Option(..., "--bucket", "-b", help="Bucket name or local directory path."),
    region: str | None = typer.Option(None, "--region", "-r", help="Region (for s3, cos)."),
    endpoint: str | None = typer.Option(None, "--endpoint", "-e", help="Endpoint URL (for oss, cos)."),
    access_key: str | None = typer.Option(None, "--access-key", "-a", help="Access key."),
    secret_key: str | None = typer.Option(None, "--secret-key", "-s", help="Secret key."),
    prefix: str = typer.Option("", "--prefix", help="Key prefix."),
) -> None:
    """Add a cloud storage configuration."""
    manager = StorageManager()
    config = StorageConfig(
        provider=provider,
        bucket=bucket,
        region=region,
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        prefix=prefix,
    )
    try:
        manager.add_storage(name, config)
        console.print(f"[green]Added storage[/green] {name} ({provider})")
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)


@storage_app.command("list")
def storage_list() -> None:
    """List all configured storage backends."""
    manager = StorageManager()
    names = manager.list_storages()
    if not names:
        console.print("[yellow]No storage configurations found.[/yellow]")
        return
    table = Table(title="Storage Configurations")
    table.add_column("Name", style="bold")
    table.add_column("Provider")
    table.add_column("Bucket")
    for name in names:
        try:
            storage = manager.get_storage(name)
            if isinstance(storage, LocalStorage):
                provider = "local"
                bucket = str(storage.base_dir)
            else:
                provider = storage.config.provider
                bucket = storage.config.bucket
            table.add_row(name, provider, bucket)
        except Exception:
            table.add_row(name, "?", "?")
    console.print(table)


@storage_app.command("upload")
def storage_upload(
    file: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True, help="File to upload."),
    storage_name: str = typer.Option(..., "--storage", "-s", help="Storage configuration name."),
    remote_key: str | None = typer.Option(None, "--key", "-k", help="Remote key (defaults to file name)."),
) -> None:
    """Upload a file to cloud storage."""
    manager = StorageManager()
    try:
        storage = manager.get_storage(storage_name)
    except KeyError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)
    key = remote_key or file.name
    try:
        url = storage.upload(file, key)
        console.print(f"[green]Uploaded[/green] {file.name} → {url}")
    except Exception as exc:
        console.print(f"[red]Upload failed:[/red] {exc}")
        raise typer.Exit(code=1)


@storage_app.command("download")
def storage_download(
    remote_key: str = typer.Argument(..., help="Remote key to download."),
    storage_name: str = typer.Option(..., "--storage", "-s", help="Storage configuration name."),
    output: Path = typer.Option(..., "--output", "-o", help="Local output path."),
) -> None:
    """Download a file from cloud storage."""
    manager = StorageManager()
    try:
        storage = manager.get_storage(storage_name)
    except KeyError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)
    try:
        storage.download(remote_key, output)
        console.print(f"[green]Downloaded[/green] {remote_key} → {output}")
    except Exception as exc:
        console.print(f"[red]Download failed:[/red] {exc}")
        raise typer.Exit(code=1)


@storage_app.command("sync")
def storage_sync(
    local_dir: Path = typer.Argument(..., exists=True, file_okay=False, readable=True, help="Local directory to sync."),
    storage_name: str = typer.Option(..., "--storage", "-s", help="Storage configuration name."),
    direction: str = typer.Option("up", "--direction", "-d", help="Sync direction: up (to cloud) or down (from cloud)."),
    remote_prefix: str = typer.Option("", "--prefix", "-p", help="Remote prefix."),
) -> None:
    """Sync a local directory with cloud storage."""
    if direction not in {"up", "down"}:
        console.print("[red]Direction must be 'up' or 'down'.[/red]")
        raise typer.Exit(code=1)
    manager = StorageManager()
    try:
        if direction == "up":
            urls = manager.sync_to_cloud(local_dir, storage_name, remote_prefix)
            console.print(f"[green]Synced {len(urls)} file(s) to cloud.[/green]")
        else:
            paths = manager.sync_from_cloud(storage_name, remote_prefix, local_dir)
            console.print(f"[green]Synced {len(paths)} file(s) from cloud.[/green]")
    except Exception as exc:
        console.print(f"[red]Sync failed:[/red] {exc}")
        raise typer.Exit(code=1)


# ------------------------------------------------------------------
# Rule engine sub-commands
# ------------------------------------------------------------------

@rule_app.command("add")
def rule_add(
    name: str = typer.Argument(..., help="Rule name."),
    condition: str = typer.Option(..., "--condition", "-c", help="Condition expression."),
    action: str = typer.Option(..., "--action", "-a", help="Action type: convert, tag, move, copy, rename, delete."),
    action_params: str = typer.Option("{}", "--params", "-p", help="Action parameters as JSON string."),
    priority: int = typer.Option(0, "--priority", help="Rule priority (higher runs first)."),
) -> None:
    """Add a batch processing rule."""
    engine = RuleEngine()
    try:
        params = json.loads(action_params)
    except json.JSONDecodeError as exc:
        console.print(f"[red]Invalid JSON params:[/red] {exc}")
        raise typer.Exit(code=1)
    rule = Rule(
        name=name,
        condition=condition,
        action=action,
        action_params=params,
        priority=priority,
    )
    engine.add_rule(rule)
    console.print(f"[green]Added rule[/green] {name}")


@rule_app.command("list")
def rule_list() -> None:
    """List all batch processing rules."""
    engine = RuleEngine()
    rules = engine.list_rules()
    if not rules:
        console.print("[yellow]No rules configured.[/yellow]")
        return
    table = Table(title="Batch Rules")
    table.add_column("Name", style="bold")
    table.add_column("Condition")
    table.add_column("Action")
    table.add_column("Priority")
    table.add_column("Enabled")
    for rule in rules:
        table.add_row(
            rule.name,
            rule.condition,
            rule.action,
            str(rule.priority),
            "yes" if rule.enabled else "no",
        )
    console.print(table)


@rule_app.command("run")
def rule_run(
    directory: Path = typer.Argument(..., exists=True, file_okay=False, readable=True, help="Directory to process."),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Process subdirectories."),
) -> None:
    """Run batch rules against all files in a directory."""
    engine = RuleEngine()
    iterator = directory.rglob("*") if recursive else directory.glob("*")
    files = [p for p in iterator if p.is_file()]
    if not files:
        console.print("[yellow]No files found.[/yellow]")
        raise typer.Exit(code=0)
    total = 0
    failures = 0
    for file_path in files:
        results = engine.evaluate(file_path)
        for rule_name, success, message in results:
            total += 1
            if not success:
                failures += 1
                console.print(f"[red]Rule '{rule_name}' failed for {file_path.name}:[/red] {message}")
            else:
                console.print(f"[green]Rule '{rule_name}'[/green] applied to {file_path.name}")
    console.print(f"Processed {len(files)} file(s), {total} rule execution(s), {failures} failure(s).")
    if failures:
        raise typer.Exit(code=1)


# ------------------------------------------------------------------
# Migrate command
# ------------------------------------------------------------------

@app.command("migrate")
def migrate_command() -> None:
    """Run data migration to the latest schema version."""
    manager = MigrationManager()
    if not manager.needs_migration():
        console.print("[green]Already at the latest schema version.[/green]")
        return

    logs = manager.migrate()
    for line in logs:
        if line.startswith("  ✓"):
            console.print(f"[green]{line}[/green]")
        elif line.startswith("  ✗"):
            console.print(f"[red]{line}[/red]")
        else:
            console.print(line)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
