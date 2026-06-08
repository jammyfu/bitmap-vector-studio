from __future__ import annotations

import csv
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import TraceOptions, TraceResult


def _history_path() -> Path:
    """Return the path to the history JSONL file."""
    return Path.home() / ".bitmap_vector_studio" / "history.jsonl"


def _ensure_history_dir() -> None:
    """Create the history directory if it does not exist."""
    _history_path().parent.mkdir(parents=True, exist_ok=True)


def _trim_history(max_entries: int = 100) -> None:
    """Trim the history file to keep only the most recent *max_entries* records."""
    path = _history_path()
    if not path.exists():
        return
    try:
        with path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
    except (OSError, UnicodeDecodeError):
        return
    if len(lines) > max_entries:
        with path.open("w", encoding="utf-8") as f:
            f.writelines(lines[-max_entries:])


def record_task(
    result: TraceResult,
    preset_name: str,
    options: TraceOptions,
    max_entries: int = 100,
) -> dict[str, Any]:
    """Record a conversion task to the history file.

    Args:
        result: The ``TraceResult`` returned by ``trace_image()``.
        preset_name: Name of the preset used for the conversion.
        options: The ``TraceOptions`` actually applied.
        max_entries: Maximum number of history entries to retain (default 100).

    Returns:
        The history record that was written.
    """
    _ensure_history_dir()

    export_formats: list[str] = []
    if result.pdf_path is not None:
        export_formats.append("pdf")
    if result.png_path is not None:
        export_formats.append("png")
    if result.eps_path is not None:
        export_formats.append("eps")

    record: dict[str, Any] = {
        "task_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input_path": str(result.input_path),
        "output_path": str(result.svg_path),
        "preset_name": preset_name,
        "options": options.__dict__,
        "stats": result.stats,
        "engine": result.engine,
        "elapsed_seconds": result.elapsed_seconds,
        "export_formats": export_formats,
    }

    path = _history_path()
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    _trim_history(max_entries)
    return record


def _read_records() -> list[dict[str, Any]]:
    """Read all valid records from the history file, newest last."""
    path = _history_path()
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except (OSError, UnicodeDecodeError):
        return []
    return records


def get_recent_tasks(limit: int = 20) -> list[dict[str, Any]]:
    """Return the most recent *limit* history records, newest first."""
    records = _read_records()
    return list(reversed(records[-limit:]))


def get_task(task_id: str) -> dict[str, Any] | None:
    """Return the history record matching *task_id*, or ``None`` if not found."""
    for record in reversed(_read_records()):
        if record.get("task_id") == task_id:
            return record
    return None


def clear_history() -> None:
    """Delete the entire history file."""
    path = _history_path()
    if path.exists():
        path.unlink()


def delete_task(task_id: str) -> bool:
    """Remove the record matching *task_id* from the history file.

    Returns:
        ``True`` if a record was removed, ``False`` otherwise.
    """
    path = _history_path()
    if not path.exists():
        return False
    try:
        with path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
    except (OSError, UnicodeDecodeError):
        return False

    new_lines: list[str] = []
    removed = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError:
            new_lines.append(line)
            continue
        if record.get("task_id") == task_id:
            removed = True
            continue
        new_lines.append(line)

    if removed:
        with path.open("w", encoding="utf-8") as f:
            f.writelines(new_lines)
    return removed


def _records_to_csv(records: list[dict[str, Any]], out_path: Path) -> None:
    """Write *records* to a CSV file."""
    if not records:
        out_path.write_text("", encoding="utf-8")
        return
    headers = list(records[0].keys())
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for record in records:
            flat = {k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in record.items()}
            writer.writerow(flat)


def _records_to_markdown(records: list[dict[str, Any]], out_path: Path) -> None:
    """Write *records* to a Markdown file as a table."""
    if not records:
        out_path.write_text("# Bitmap Vector Studio History Report\n\nNo records.\n", encoding="utf-8")
        return
    headers = list(records[0].keys())
    lines: list[str] = [
        "# Bitmap Vector Studio History Report",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for record in records:
        row = []
        for h in headers:
            cell = record.get(h, "")
            if isinstance(cell, (dict, list)):
                cell = json.dumps(cell, ensure_ascii=False)
            cell = str(cell).replace("|", "\\|").replace("\n", " ")
            row.append(cell)
        lines.append("| " + " | ".join(row) + " |")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def export_report(path: Path, limit: int = 50) -> None:
    """Export the most recent *limit* history records to *path*.

    The output format is determined by the file extension:
    - ``.csv`` → CSV
    - ``.md`` or ``.markdown`` → Markdown table
    - Anything else → raises ``ValueError``
    """
    records = get_recent_tasks(limit)
    # Reverse so the report lists oldest → newest.
    records = list(reversed(records))
    suffix = path.suffix.lower()
    if suffix == ".csv":
        _records_to_csv(records, path)
    elif suffix in {".md", ".markdown"}:
        _records_to_markdown(records, path)
    else:
        raise ValueError(f"Unsupported report format: {suffix}. Use .csv or .md")


def get_task_options(task_id: str) -> TraceOptions:
    """Reconstruct a ``TraceOptions`` object from a history record.

    Args:
        task_id: The UUID of the task to look up.

    Returns:
        A ``TraceOptions`` instance populated with the stored parameters.

    Raises:
        KeyError: If the task is not found.
        ValueError: If the stored options are incompatible with the current model.
    """
    record = get_task(task_id)
    if record is None:
        raise KeyError(f"Task not found: {task_id}")
    options_dict = record.get("options", {})
    # Filter to fields that exist on the current TraceOptions dataclass.
    valid_fields = {f for f in TraceOptions.__dataclass_fields__}
    filtered = {k: v for k, v in options_dict.items() if k in valid_fields}
    try:
        return TraceOptions(**filtered)
    except TypeError as exc:
        raise ValueError(f"Stored options are incompatible with current TraceOptions: {exc}") from exc
