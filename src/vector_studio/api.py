from __future__ import annotations

import json
import shutil
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Any

try:
    from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse, JSONResponse
    from pydantic import BaseModel
    _HAS_FASTAPI = True
except ImportError as exc:
    raise RuntimeError(
        "FastAPI is not installed. Install API dependencies with "
        "'pip install bitmap-vector-studio[api]'"
    ) from exc

from . import __version__
from .models import TraceOptions, TraceResult
from .presets import PRESETS, options_from_preset
from .smart_recommend import recommend_for_image
from .svg_tools import export_svg_to_pdf, export_svg_to_png
from .task_queue import TaskQueue
from .tracer import SUPPORTED_EXTENSIONS, trace_image

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------

_api_temp_dir: Path | None = None
_api_temp_lock = threading.Lock()

_task_queue: TaskQueue | None = None
_queue_lock = threading.Lock()


def _get_api_temp_dir() -> Path:
    """Return the persistent API temporary directory (created on first call)."""
    global _api_temp_dir
    if _api_temp_dir is None:
        with _api_temp_lock:
            if _api_temp_dir is None:
                _api_temp_dir = Path(tempfile.mkdtemp(prefix="vs-api-"))
    return _api_temp_dir


def _get_queue() -> TaskQueue:
    """Return the global TaskQueue singleton (started on first call)."""
    global _task_queue
    if _task_queue is None:
        with _queue_lock:
            if _task_queue is None:
                _task_queue = TaskQueue(max_workers=4, output_dir=_get_api_temp_dir())
                _task_queue.start()
    return _task_queue


def _cleanup_api_temp() -> None:
    """Remove the persistent API temporary directory."""
    global _api_temp_dir
    with _api_temp_lock:
        if _api_temp_dir is not None and _api_temp_dir.exists():
            shutil.rmtree(_api_temp_dir, ignore_errors=True)
            _api_temp_dir = None


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ConvertAsyncResponse(BaseModel):
    task_id: str
    status: str


class StatusResponse(BaseModel):
    task_id: str
    status: str
    progress: float
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class PresetInfo(BaseModel):
    name: str
    colormode: str
    hierarchical: str
    mode: str
    color_precision: int
    layer_difference: int
    filter_speckle: int


class RecommendResponse(BaseModel):
    preset: str
    confidence: float
    reason: str
    features: dict[str, Any]


class BatchResponse(BaseModel):
    task_ids: list[str]


class HealthResponse(BaseModel):
    status: str
    version: str


class ErrorResponse(BaseModel):
    detail: str


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Bitmap Vector Studio API",
    description="RESTful API for bitmap-to-SVG vector conversion powered by VTracer.",
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_options(options: str) -> dict[str, Any]:
    """Parse the *options* JSON string into a dictionary."""
    if not options or options == "{}":
        return {}
    try:
        parsed = json.loads(options)
        if not isinstance(parsed, dict):
            raise ValueError("Options must be a JSON object.")
        return parsed
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid options JSON: {exc}") from exc


def _save_upload(file: UploadFile, dest_dir: Path) -> Path:
    """Persist an uploaded file to *dest_dir* and return its path."""
    safe_name = file.filename or f"upload_{uuid.uuid4()}"
    safe_name = Path(safe_name).name
    path = dest_dir / safe_name
    path.write_bytes(file.file.read())
    return path


def _validate_extension(path: Path) -> None:
    """Raise HTTPException if the file extension is not supported."""
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        valid = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported input format: {path.suffix}. Supported: {valid}",
        )


def _build_preset_info(name: str, opts: TraceOptions) -> PresetInfo:
    """Build a PresetInfo model from a preset name and TraceOptions."""
    return PresetInfo(
        name=name,
        colormode=opts.colormode,
        hierarchical=opts.hierarchical,
        mode=opts.mode,
        color_precision=opts.color_precision,
        layer_difference=opts.layer_difference,
        filter_speckle=opts.filter_speckle,
    )


def _run_sync_conversion(
    input_path: Path,
    output_path: Path,
    opts: TraceOptions,
) -> TraceResult:
    """Wrapper around trace_image for the sync endpoint."""
    return trace_image(input_path, output_path, opts, optimize=True, optimize_level="basic")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post(
    "/convert",
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def convert(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    preset: str = Form("poster"),
    options: str = Form("{}"),
):
    """Convert a single image synchronously and return the SVG file."""
    overrides = _parse_options(options)
    try:
        opts = options_from_preset(preset, overrides)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    tmpdir = Path(tempfile.mkdtemp(prefix="vs-sync-"))
    input_path = _save_upload(file, tmpdir)
    _validate_extension(input_path)
    output_path = tmpdir / f"{input_path.stem}.svg"

    try:
        result = _run_sync_conversion(input_path, output_path, opts)
    except Exception as exc:
        background_tasks.add_task(shutil.rmtree, tmpdir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Conversion failed: {exc}") from exc

    if not result.svg_path.exists():
        background_tasks.add_task(shutil.rmtree, tmpdir, ignore_errors=True)
        raise HTTPException(status_code=500, detail="SVG output was not generated.")

    background_tasks.add_task(shutil.rmtree, tmpdir, ignore_errors=True)
    return FileResponse(
        path=result.svg_path,
        media_type="image/svg+xml",
        filename=f"{input_path.stem}.svg",
    )


@app.post(
    "/convert/async",
    responses={
        400: {"model": ErrorResponse},
    },
)
async def convert_async(
    file: UploadFile,
    preset: str = Form("poster"),
    options: str = Form("{}"),
):
    """Start an asynchronous conversion and return the task ID."""
    overrides = _parse_options(options)
    try:
        opts = options_from_preset(preset, overrides)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    api_dir = _get_api_temp_dir()
    upload_dir = api_dir / "uploads" / str(uuid.uuid4())
    upload_dir.mkdir(parents=True, exist_ok=True)
    input_path = _save_upload(file, upload_dir)
    _validate_extension(input_path)
    output_path = upload_dir / f"{input_path.stem}.svg"

    q = _get_queue()
    task_id = q.add_task(input_path, output_path, opts, optimize_level="basic")
    return ConvertAsyncResponse(task_id=task_id, status="pending")


@app.get(
    "/status/{task_id}",
    responses={
        404: {"model": ErrorResponse},
    },
)
async def get_status(task_id: str):
    """Query the status of an asynchronous conversion task."""
    q = _get_queue()
    status = q.get_status(task_id)
    if status["status"] == "unknown":
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    return StatusResponse(**status)


@app.get(
    "/download/{task_id}/{format}",
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def download(task_id: str, format: str = "svg"):
    """Download the result of a completed conversion task."""
    fmt = format.lower()
    if fmt not in {"svg", "pdf", "png"}:
        raise HTTPException(status_code=400, detail="Format must be one of: svg, pdf, png.")

    q = _get_queue()
    status = q.get_status(task_id)
    if status["status"] == "unknown":
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    if status["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Task is not completed yet. Current status: {status['status']}",
        )

    result = status.get("result", {}) or {}
    svg_path_str = result.get("svg_path")
    if not svg_path_str:
        raise HTTPException(status_code=404, detail="No output file available.")

    svg_path = Path(svg_path_str)
    if not svg_path.exists():
        raise HTTPException(status_code=404, detail="Output file no longer exists.")

    if fmt == "svg":
        return FileResponse(
            path=svg_path,
            media_type="image/svg+xml",
            filename=svg_path.name,
        )

    if fmt == "pdf":
        pdf_path = svg_path.with_suffix(".pdf")
        if not pdf_path.exists():
            try:
                pdf_path = export_svg_to_pdf(svg_path, pdf_path)
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"PDF export failed: {exc}") from exc
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=pdf_path.name,
        )

    if fmt == "png":
        png_path = svg_path.with_suffix(".png")
        if not png_path.exists():
            try:
                png_path = export_svg_to_png(svg_path, png_path)
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"PNG export failed: {exc}") from exc
        return FileResponse(
            path=png_path,
            media_type="image/png",
            filename=png_path.name,
        )

    # Unreachable – guarded by the fmt check above.
    raise HTTPException(status_code=400, detail="Unsupported format.")


@app.get("/presets")
async def list_presets():
    """List all available tracing presets."""
    return [_build_preset_info(name, opts) for name, opts in PRESETS.items()]


@app.post(
    "/recommend",
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def recommend(file: UploadFile, background_tasks: BackgroundTasks):
    """Analyze an uploaded image and recommend the best tracing preset."""
    tmpdir = Path(tempfile.mkdtemp(prefix="vs-rec-"))
    input_path = _save_upload(file, tmpdir)
    _validate_extension(input_path)

    try:
        preset, confidence, reason, features = recommend_for_image(input_path)
    except Exception as exc:
        background_tasks.add_task(shutil.rmtree, tmpdir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {exc}") from exc

    background_tasks.add_task(shutil.rmtree, tmpdir, ignore_errors=True)
    return RecommendResponse(
        preset=preset,
        confidence=confidence,
        reason=reason,
        features=features,
    )


@app.post(
    "/batch",
    responses={
        400: {"model": ErrorResponse},
    },
)
async def batch_convert(
    files: list[UploadFile],
    preset: str = Form("poster"),
    options: str = Form("{}"),
):
    """Batch-convert multiple images asynchronously."""
    overrides = _parse_options(options)
    try:
        opts = options_from_preset(preset, overrides)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    q = _get_queue()
    api_dir = _get_api_temp_dir()
    task_ids: list[str] = []

    for file in files:
        upload_dir = api_dir / "uploads" / str(uuid.uuid4())
        upload_dir.mkdir(parents=True, exist_ok=True)
        input_path = _save_upload(file, upload_dir)
        if input_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            valid = ", ".join(sorted(SUPPORTED_EXTENSIONS))
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unsupported input format for {file.filename}: "
                    f"{input_path.suffix}. Supported: {valid}"
                ),
            )
        output_path = upload_dir / f"{input_path.stem}.svg"
        task_ids.append(q.add_task(input_path, output_path, opts, optimize_level="basic"))

    return BatchResponse(task_ids=task_ids)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="ok", version=__version__)
