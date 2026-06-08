from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .checkpoint import CheckpointManager
from .cloud_sync import CloudSyncManager, GitHubGistBackend, LocalServerBackend
from .config import Config
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
    PluginValidator,
)
from .community_tools import (
    ContributionGuideGenerator,
    PresetValidator,
)
from .plugins import PluginManager
from .presets import PRESETS, options_from_preset
from .svg_optimizer import svg_quality_score
from .svg_tools import svg_stats
from .task_queue import TaskQueue
from .tracer import SUPPORTED_EXTENSIONS, trace_image
from .workspace import Workspace, WorkspaceManager

console = Console()
app = typer.Typer(
    help="Bitmap Vector Studio: Illustrator-like bitmap to SVG conversion powered by VTracer.",
    no_args_is_help=True,
)

# Sub-typer for queue commands
queue_app = typer.Typer(help="Task queue management.")
app.add_typer(queue_app, name="queue")

# Sub-typer for config commands
config_app = typer.Typer(help="Configuration management.")
app.add_typer(config_app, name="config")

# Sub-typer for plugin commands
plugin_app = typer.Typer(help="Plugin management.")
app.add_typer(plugin_app, name="plugin")

# Sub-typer for market commands
market_app = typer.Typer(help="Preset market management.")
app.add_typer(market_app, name="market")

# Sub-typer for workspace commands
workspace_app = typer.Typer(help="Workspace management.")
app.add_typer(workspace_app, name="workspace")

# Sub-typer for OCR commands
ocr_app = typer.Typer(help="OCR utilities.")
app.add_typer(ocr_app, name="ocr")

# Sub-typer for engine commands
engine_app = typer.Typer(help="Vectorization engine management.")
app.add_typer(engine_app, name="engine")

# Sub-typer for validate commands
validate_app = typer.Typer(help="Validation utilities.")
app.add_typer(validate_app, name="validate")

# Sub-typer for contrib commands
contrib_app = typer.Typer(help="Community contributor tools.")
app.add_typer(contrib_app, name="contrib")

# Sub-typer for cloud sync commands
cloud_app = typer.Typer(help="Cloud sync and sharing.")
app.add_typer(cloud_app, name="cloud")

# Conditional import so tests can patch vector_studio.cli.uvicorn.run
try:
    import uvicorn
except ImportError:  # pragma: no cover
    uvicorn = None  # type: ignore[assignment]


@app.command("api")
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
) -> None:
    """Global callback that intercepts --api before any sub-command runs."""
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


@app.command("presets")
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


@app.command("trace")
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
) -> None:
    """Convert one bitmap image to SVG."""
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


@app.command("benchmark")
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


@app.command("batch")
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
    """Batch-convert a folder of images."""
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
        console.print("[yellow]No supported images found.[/yellow]")
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


@app.command("search")
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
# Resume command
# ------------------------------------------------------------------

@app.command("resume")
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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
