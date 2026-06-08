from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .external_editors import open_with_default_editor, open_with_editor
from .presets import PRESETS, options_from_preset
from .tracer import SUPPORTED_EXTENSIONS, trace_image

console = Console()
app = typer.Typer(
    help="Bitmap Vector Studio: Illustrator-like bitmap to SVG conversion powered by VTracer.",
    no_args_is_help=True,
)


def _option_overrides(**kwargs):
    return {key: value for key, value in kwargs.items() if value is not None}


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
    name_layers: bool = typer.Option(False, "--name-layers", help="Add meaningful layer names to the output SVG."),
    export_pdf: bool = typer.Option(False, "--export-pdf", help="Also export PDF via CairoSVG."),
    export_png: bool = typer.Option(False, "--export-png", help="Also export PNG preview via CairoSVG."),
    export_eps: bool = typer.Option(False, "--export-eps", help="Also export EPS via Inkscape CLI."),
    open_editor: Optional[str] = typer.Option(None, "--open", help="Open the output SVG in an external editor (inkscape, illustrator, etc.). Use without value for default editor."),
) -> None:
    """Convert one bitmap image to SVG."""
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
    result = trace_image(
        input_path,
        out,
        opts,
        optimize=optimize,
        name_layers=name_layers,
        export_pdf=export_pdf,
        export_png=export_png,
        export_eps=export_eps,
    )

    console.print(f"[green]Done[/green] {result.svg_path}")
    console.print(f"Engine: {result.engine} | Time: {result.elapsed_seconds:.2f}s")
    console.print(f"Stats: {result.stats}")
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
    export_pdf: bool = typer.Option(False, "--export-pdf"),
    export_png: bool = typer.Option(False, "--export-png"),
    open_editor: bool = typer.Option(False, "--open", help="Open each output SVG in the default external editor after conversion."),
) -> None:
    """Batch-convert a folder of images."""
    output_dir.mkdir(parents=True, exist_ok=True)
    opts = options_from_preset(preset)
    iterator = input_dir.rglob("*") if recursive else input_dir.glob("*")
    images = [path for path in iterator if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS]

    if not images:
        console.print("[yellow]No supported images found.[/yellow]")
        raise typer.Exit(code=0)

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
            result = trace_image(image_path, out_path, opts, export_pdf=export_pdf, export_png=export_png, name_layers=name_layers)
            table.add_row(str(image_path), str(result.svg_path), "ok")
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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
