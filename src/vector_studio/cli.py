from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .config import Config
from .external_editors import open_with_default_editor, open_with_editor
from .param_search import ParamGrid, quick_search, search_best_params
from .plugin_interface import Plugin
from .plugins import PluginManager
from .presets import PRESETS, options_from_preset
from .svg_optimizer import svg_quality_score
from .svg_tools import svg_stats
from .task_queue import TaskQueue
from .tracer import SUPPORTED_EXTENSIONS, trace_image

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
    recommend: bool = typer.Option(False, "--recommend", help="Only analyze and recommend a preset, do not convert."),
    config_path: Optional[Path] = typer.Option(None, "--config", help="Path to configuration file."),
    plugin: list[str] = typer.Option([], "--plugin", help="Enable a plugin by name (can be used multiple times)."),
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

    result = trace_image(
        input_path,
        out,
        opts,
        optimize=optimize,
        optimize_level=optimize_level,
        name_layers=name_layers,
        export_pdf=export_pdf,
        export_png=export_png,
        export_eps=export_eps,
        smart_remove_bg=smart_remove_bg,
        enhance=enhance,
        plugins=plugins,
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
    q = TaskQueue(max_workers=workers, output_dir=output_dir, max_retries=retry)
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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
