from __future__ import annotations

import base64
import json
import shutil
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any

try:
    from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
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
from .cloud_sync import CloudSyncManager, LocalServerBackend
from .collaboration import (
    CollabManager,
    CollabRoom,
    Operation,
    get_collab_manager,
)
from .models import TraceOptions, TraceResult
from .presets import PRESETS, options_from_preset
from .smart_recommend import recommend_for_image
from .render_farm import RenderFarm, RenderTask, WorkerNode
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

_share_manager: CloudSyncManager | None = None
_share_lock = threading.Lock()

_render_farm: RenderFarm | None = None
_farm_lock = threading.Lock()


def _get_render_farm() -> RenderFarm:
    """Return the global RenderFarm singleton (created on first call)."""
    global _render_farm
    if _render_farm is None:
        with _farm_lock:
            if _render_farm is None:
                _render_farm = RenderFarm()
                _render_farm.start_heartbeat_monitor()
    return _render_farm


def _get_share_manager() -> CloudSyncManager:
    """Return the global CloudSyncManager singleton (created on first call)."""
    global _share_manager
    if _share_manager is None:
        with _share_lock:
            if _share_manager is None:
                backend = LocalServerBackend(
                    storage_dir=_get_api_temp_dir() / "shares",
                    base_url="http://localhost:8000",
                )
                _share_manager = CloudSyncManager(backend)
    return _share_manager


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
    global _api_temp_dir, _share_manager
    with _api_temp_lock:
        if _api_temp_dir is not None and _api_temp_dir.exists():
            shutil.rmtree(_api_temp_dir, ignore_errors=True)
            _api_temp_dir = None
    with _share_lock:
        _share_manager = None


from .health_check import HealthChecker, check_disk_space, check_memory, check_python_deps, check_vtracer
from .metrics import get_metrics

# 初始化健康检查器
_health_checker = HealthChecker()
_health_checker.register("disk", lambda: check_disk_space())
_health_checker.register("memory", lambda: check_memory())
_health_checker.register("deps", lambda: check_python_deps())
_health_checker.register("vtracer", lambda: check_vtracer())


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


class ShareResponse(BaseModel):
    url: str
    qr_code: str
    expire_at: str
    file_id: str


class ShareListResponse(BaseModel):
    shares: list[dict[str, Any]]


class ShareRevokeResponse(BaseModel):
    success: bool


class ShareQrResponse(BaseModel):
    qr_code: str


# ---------------------------------------------------------------------------
# Collaboration Pydantic models
# ---------------------------------------------------------------------------

class RoomCreateResponse(BaseModel):
    room_id: str
    owner: str
    created_at: str


class RoomStateResponse(BaseModel):
    room_id: str
    owner: str
    created_at: str
    params: dict[str, Any]
    preview: Any | None = None
    files: list[dict[str, Any]]
    last_convert: dict[str, Any] | None = None
    client_count: int
    operation_count: int
    next_version: int


class OperationRequest(BaseModel):
    op_id: str | None = None
    client_id: str
    type: str
    data: dict[str, Any] = {}
    version: int | None = None


class OperationResponse(BaseModel):
    op_id: str
    status: str
    version: int | None = None
    state: dict[str, Any] | None = None
    reason: str | None = None
    expected_version: int | None = None


class HistoryResponse(BaseModel):
    operations: list[dict[str, Any]]


class RoomListResponse(BaseModel):
    rooms: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Render farm Pydantic models
# ---------------------------------------------------------------------------

class FarmTaskSubmitResponse(BaseModel):
    task_id: str
    status: str


class FarmTaskStatusResponse(BaseModel):
    task_id: str
    status: str
    input_path: str | None = None
    output_path: str | None = None
    assigned_worker: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class FarmWorkerRegisterRequest(BaseModel):
    worker_id: str
    host: str
    port: int
    capacity: int = 4


class FarmWorkerRegisterResponse(BaseModel):
    success: bool
    worker_id: str


class FarmWorkersListResponse(BaseModel):
    workers: list[dict[str, Any]]


class FarmStatusResponse(BaseModel):
    workers: list[dict[str, Any]]
    tasks: list[dict[str, Any]]
    summary: dict[str, Any]


class FarmHeartbeatResponse(BaseModel):
    ok: bool


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
    status = _health_checker.check()
    return status.to_dict()


@app.get("/metrics")
async def get_metrics_endpoint():
    """Performance metrics endpoint."""
    return get_metrics().get_snapshot()


@app.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe."""
    status = _health_checker.check()
    if status.status == "unhealthy":
        raise HTTPException(status_code=503, detail="Service not ready")
    return {"ready": True}


@app.get("/live")
async def liveness_check():
    """Kubernetes liveness probe."""
    return {"alive": True}


# ---------------------------------------------------------------------------
# Share endpoints
# ---------------------------------------------------------------------------

@app.post(
    "/share",
    response_model=ShareResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def share_svg(file: UploadFile, expire_hours: int = 24):
    """Upload an SVG file and return a share link with QR code."""
    tmpdir = Path(tempfile.mkdtemp(prefix="vs-share-"))
    safe_name = file.filename or f"upload_{uuid.uuid4()}.svg"
    safe_name = Path(safe_name).name
    input_path = tmpdir / safe_name
    input_path.write_bytes(file.file.read())

    if input_path.suffix.lower() != ".svg":
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise HTTPException(status_code=400, detail="Only SVG files are supported for sharing.")

    try:
        manager = _get_share_manager()
        result = manager.share_svg(input_path, expire_hours=expire_hours)
    except Exception as exc:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Share failed: {exc}") from exc

    shutil.rmtree(tmpdir, ignore_errors=True)
    return ShareResponse(**result)


@app.get(
    "/share/{share_id}",
    responses={
        404: {"model": ErrorResponse},
    },
)
async def get_shared_svg(share_id: str):
    """Retrieve a shared SVG by its share ID."""
    backend = _get_share_manager().backend
    if isinstance(backend, LocalServerBackend):
        file_path = backend.storage_dir / share_id
        meta = backend._shares.get(share_id)
        if not meta or not file_path.exists():
            raise HTTPException(status_code=404, detail="Share not found.")
        if backend._is_expired(share_id):
            raise HTTPException(status_code=404, detail="Share has expired.")
        return FileResponse(
            path=file_path,
            media_type=meta.get("content_type", "image/svg+xml"),
            filename=meta.get("filename", share_id),
        )
    raise HTTPException(status_code=501, detail="Only LocalServerBackend supports direct download.")


@app.delete(
    "/share/{share_id}",
    response_model=ShareRevokeResponse,
    responses={
        404: {"model": ErrorResponse},
    },
)
async def revoke_share(share_id: str):
    """Revoke a shared SVG by its share ID."""
    manager = _get_share_manager()
    success = manager.revoke_share(share_id)
    if not success:
        raise HTTPException(status_code=404, detail="Share not found.")
    return ShareRevokeResponse(success=True)


@app.get(
    "/shares",
    response_model=ShareListResponse,
)
async def list_shares():
    """List all active shares."""
    manager = _get_share_manager()
    shares = manager.get_shared_files()
    return ShareListResponse(shares=shares)


@app.get(
    "/share/{share_id}/qr",
    response_model=ShareQrResponse,
    responses={
        404: {"model": ErrorResponse},
    },
)
async def get_share_qr(share_id: str):
    """Get the QR code (base64 PNG) for a share."""
    manager = _get_share_manager()
    backend = manager.backend
    if isinstance(backend, LocalServerBackend):
        if backend._is_expired(share_id) or share_id not in backend._shares:
            raise HTTPException(status_code=404, detail="Share not found or expired.")
    qr_bytes = backend.get_qr_code(share_id)
    qr_b64 = base64.b64encode(qr_bytes).decode("ascii")
    return ShareQrResponse(qr_code=qr_b64)


# ---------------------------------------------------------------------------
# Collaboration endpoints
# ---------------------------------------------------------------------------

@app.websocket("/ws/collab/{room_id}")
async def collab_websocket(websocket: WebSocket, room_id: str):
    """WebSocket endpoint for real-time collaboration in a room.

    Clients must connect with a query parameter ``client_id``.
    Messages are JSON dictionaries. Supported client events:

    * ``{"event": "join", "client_id": "..."}`` – handshake
    * ``{"event": "operation", "op": {...}}`` – submit an operation
    * ``{"event": "ping"}`` – keep-alive
    """
    await websocket.accept()
    client_id: str | None = None
    manager = await get_collab_manager()

    try:
        while True:
            raw = await websocket.receive_json()
            event = raw.get("event")

            if event == "join":
                client_id = raw.get("client_id", str(uuid.uuid4())[:8])
                room = manager.get_room(room_id)
                if room is None:
                    await websocket.send_json({"event": "error", "detail": "Room not found."})
                    await websocket.close()
                    return
                await manager.join_room(room_id, client_id, websocket)
                await websocket.send_json({
                    "event": "joined",
                    "room_id": room_id,
                    "client_id": client_id,
                    "state": room.get_state_snapshot(),
                })

            elif event == "operation":
                if client_id is None:
                    await websocket.send_json({"event": "error", "detail": "Send 'join' first."})
                    continue
                op_raw = raw.get("op", {})
                op = Operation(
                    op_id=op_raw.get("op_id", str(uuid.uuid4())[:12]),
                    client_id=client_id,
                    timestamp=time.time(),
                    type=op_raw.get("type", "unknown"),
                    data=op_raw.get("data", {}),
                    version=op_raw.get("version", 1),
                )
                room = manager.get_room(room_id)
                if room is None:
                    await websocket.send_json({"event": "error", "detail": "Room not found."})
                    continue
                result = await room.apply_operation(op)
                await websocket.send_json({"event": "operation_result", "result": result})

            elif event == "ping":
                await websocket.send_json({"event": "pong", "timestamp": time.time()})

            else:
                await websocket.send_json({"event": "error", "detail": f"Unknown event: {event}"})

    except WebSocketDisconnect:
        if client_id:
            await manager.leave_room(room_id, client_id)
    except Exception as exc:  # pragma: no cover
        if client_id:
            await manager.leave_room(room_id, client_id)
        raise


@app.post("/collab/rooms", response_model=RoomCreateResponse)
async def create_room(owner: str):
    """Create a new collaboration room.

    Parameters
    ----------
    owner:
        User identifier that owns the room.
    """
    manager = await get_collab_manager()
    room_id = await manager.create_room(owner)
    room = manager.get_room(room_id)
    if room is None:  # pragma: no cover
        raise HTTPException(status_code=500, detail="Room creation failed.")
    return RoomCreateResponse(
        room_id=room_id,
        owner=room.owner,
        created_at=room.created_at,
    )


@app.get("/collab/rooms/{room_id}", response_model=RoomStateResponse)
async def get_room_state(room_id: str):
    """Get the current state snapshot of a collaboration room.

    Returns 404 if the room does not exist.
    """
    manager = await get_collab_manager()
    room = manager.get_room(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found.")
    snap = room.get_state_snapshot()
    return RoomStateResponse(**snap)


@app.post("/collab/rooms/{room_id}/operations", response_model=OperationResponse)
async def submit_operation(room_id: str, operation: OperationRequest):
    """Submit an operation to a room via HTTP (non-WebSocket path).

    Useful for CLI clients or integrations that do not maintain a
    persistent WebSocket connection.
    """
    manager = await get_collab_manager()
    room = manager.get_room(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found.")

    op = Operation(
        op_id=operation.op_id or str(uuid.uuid4())[:12],
        client_id=operation.client_id,
        timestamp=time.time(),
        type=operation.type,
        data=operation.data,
        version=operation.version or 1,
    )
    result = await room.apply_operation(op)
    return OperationResponse(**result)


@app.get("/collab/rooms/{room_id}/history", response_model=HistoryResponse)
async def get_operation_history(room_id: str, limit: int = 100):
    """Retrieve the most recent operations for a room.

    Parameters
    ----------
    room_id:
        Target room identifier.
    limit:
        Maximum number of operations to return (default 100).
    """
    manager = await get_collab_manager()
    room = manager.get_room(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found.")
    ops = room.get_history(limit=limit)
    return HistoryResponse(operations=ops)


@app.get("/collab/rooms", response_model=RoomListResponse)
async def list_rooms():
    """List all active collaboration rooms."""
    manager = await get_collab_manager()
    rooms = manager.list_rooms()
    return RoomListResponse(rooms=rooms)


# ---------------------------------------------------------------------------
# Render farm endpoints
# ---------------------------------------------------------------------------

@app.post("/farm/submit", response_model=FarmTaskSubmitResponse)
async def submit_farm_task(
    file: UploadFile,
    preset: str = Form("poster"),
    options: str = Form("{}"),
    priority: int = Form(0),
):
    """Submit a single image conversion to the distributed render farm."""
    overrides = _parse_options(options)
    try:
        opts = options_from_preset(preset, overrides)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    api_dir = _get_api_temp_dir()
    upload_dir = api_dir / "farm_uploads" / str(uuid.uuid4())
    upload_dir.mkdir(parents=True, exist_ok=True)
    input_path = _save_upload(file, upload_dir)
    _validate_extension(input_path)
    output_path = upload_dir / f"{input_path.stem}.svg"

    task = RenderTask(
        task_id=str(uuid.uuid4()),
        input_path=input_path,
        output_path=output_path,
        options=opts,
        priority=priority,
    )
    farm = _get_render_farm()
    task_id = farm.submit_task(task)
    return FarmTaskSubmitResponse(task_id=task_id, status=task.status)


@app.get("/farm/status/{task_id}", response_model=FarmTaskStatusResponse)
async def get_farm_task_status(task_id: str):
    """Query the status of a farm-render task."""
    farm = _get_render_farm()
    status = farm.get_task_status(task_id)
    if status["status"] == "unknown":
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    return FarmTaskStatusResponse(
        task_id=status["task_id"],
        status=status["status"],
        input_path=status.get("input_path"),
        output_path=status.get("output_path"),
        assigned_worker=status.get("assigned_worker"),
        started_at=status.get("started_at"),
        completed_at=status.get("completed_at"),
    )


@app.get("/farm/workers", response_model=FarmWorkersListResponse)
async def list_workers():
    """List all registered render-farm workers."""
    farm = _get_render_farm()
    status = farm.get_farm_status()
    return FarmWorkersListResponse(workers=status["workers"])


@app.post("/farm/workers/register", response_model=FarmWorkerRegisterResponse)
async def register_worker(request: FarmWorkerRegisterRequest):
    """Register a new worker node with the farm coordinator."""
    farm = _get_render_farm()
    worker = WorkerNode(
        worker_id=request.worker_id,
        host=request.host,
        port=request.port,
        capacity=request.capacity,
    )
    success = farm.register_worker(worker)
    return FarmWorkerRegisterResponse(success=success, worker_id=request.worker_id)


@app.post("/farm/workers/{worker_id}/heartbeat", response_model=FarmHeartbeatResponse)
async def worker_heartbeat(worker_id: str):
    """Receive a heartbeat from a worker node."""
    farm = _get_render_farm()
    with farm._lock:
        worker = farm._workers.get(worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail=f"Worker not found: {worker_id}")
    worker.update_heartbeat()
    return FarmHeartbeatResponse(ok=True)


@app.get("/farm/status", response_model=FarmStatusResponse)
async def get_farm_status():
    """Return the overall status of the render farm."""
    farm = _get_render_farm()
    return FarmStatusResponse(**farm.get_farm_status())
