import json
from pathlib import Path

import pytest

from vector_studio.history import (
    clear_history,
    delete_task,
    export_report,
    get_recent_tasks,
    get_task,
    get_task_options,
    record_task,
    _history_path,
)
from vector_studio.models import TraceOptions, TraceResult


@pytest.fixture(autouse=True)
def _clean_history(monkeypatch, tmp_path):
    """Redirect history to a temporary file for every test."""
    fake_history = tmp_path / "history.jsonl"
    monkeypatch.setattr(
        "vector_studio.history._history_path",
        lambda: fake_history,
    )
    yield


def _make_result(
    tmp_path: Path,
    *,
    export_pdf: bool = False,
    export_png: bool = False,
    export_eps: bool = False,
) -> TraceResult:
    svg = tmp_path / "out.svg"
    svg.write_text('<svg viewBox="0 0 10 10"><path d="M0 0"/></svg>', encoding="utf-8")
    return TraceResult(
        input_path=tmp_path / "in.png",
        svg_path=svg,
        engine="python-vtracer",
        elapsed_seconds=1.23,
        stats={"paths": 1, "file_bytes": 123},
        pdf_path=svg.with_suffix(".pdf") if export_pdf else None,
        png_path=svg.with_suffix(".png") if export_png else None,
        eps_path=svg.with_suffix(".eps") if export_eps else None,
    )


def test_record_task_creates_file(tmp_path: Path):
    result = _make_result(tmp_path)
    record = record_task(result, "default", TraceOptions())
    # The autouse fixture redirects history to tmp_path / "history.jsonl"
    assert (tmp_path / "history.jsonl").exists()
    assert record["task_id"]
    assert record["preset_name"] == "default"
    assert record["engine"] == "python-vtracer"
    assert record["elapsed_seconds"] == 1.23
    assert record["export_formats"] == []


def test_record_task_with_exports(tmp_path: Path):
    result = _make_result(tmp_path, export_pdf=True, export_png=True, export_eps=True)
    record = record_task(result, "poster", TraceOptions())
    assert sorted(record["export_formats"]) == ["eps", "pdf", "png"]


def test_get_recent_tasks_order_and_limit(tmp_path: Path):
    for i in range(5):
        result = _make_result(tmp_path)
        result.stats["idx"] = i
        record_task(result, "default", TraceOptions())
    recent = get_recent_tasks(limit=3)
    assert len(recent) == 3
    # Newest first
    assert recent[0]["stats"]["idx"] == 4
    assert recent[1]["stats"]["idx"] == 3
    assert recent[2]["stats"]["idx"] == 2


def test_get_task_and_delete_task(tmp_path: Path):
    result = _make_result(tmp_path)
    record = record_task(result, "default", TraceOptions())
    tid = record["task_id"]

    found = get_task(tid)
    assert found is not None
    assert found["task_id"] == tid

    assert delete_task(tid) is True
    assert get_task(tid) is None
    assert delete_task(tid) is False


def test_clear_history(tmp_path: Path):
    for _ in range(3):
        record_task(_make_result(tmp_path), "default", TraceOptions())
    assert len(get_recent_tasks(limit=100)) == 3
    clear_history()
    assert len(get_recent_tasks(limit=100)) == 0
    assert not (tmp_path / "history.jsonl").exists()


def test_max_entries_trimming(tmp_path: Path):
    for i in range(10):
        result = _make_result(tmp_path)
        result.stats["idx"] = i
        record_task(result, "default", TraceOptions(), max_entries=5)
    all_records = get_recent_tasks(limit=100)
    assert len(all_records) == 5
    # Newest first, so idx 9, 8, 7, 6, 5
    assert [r["stats"]["idx"] for r in all_records] == [9, 8, 7, 6, 5]


def test_get_task_options_roundtrip(tmp_path: Path):
    original = TraceOptions(
        colormode="binary",
        hierarchical="cutout",
        mode="polygon",
        filter_speckle=8,
        color_precision=4,
        layer_difference=32,
        corner_threshold=90,
        length_threshold=5.5,
        max_iterations=20,
        splice_threshold=60,
        path_precision=5,
        denoise=True,
        posterize=4,
        max_input_side=1024,
        alpha_background="#000000",
    )
    result = _make_result(tmp_path)
    record = record_task(result, "custom", original)
    restored = get_task_options(record["task_id"])
    assert restored == original


def test_get_task_options_missing_task():
    with pytest.raises(KeyError, match="not-found-uuid"):
        get_task_options("not-found-uuid")


def test_export_report_csv(tmp_path: Path):
    for _ in range(3):
        record_task(_make_result(tmp_path), "default", TraceOptions())
    csv_path = tmp_path / "report.csv"
    export_report(csv_path, limit=2)
    text = csv_path.read_text(encoding="utf-8")
    lines = text.strip().splitlines()
    assert lines[0].startswith("task_id")
    # header + 2 data rows
    assert len(lines) == 3


def test_export_report_markdown(tmp_path: Path):
    for _ in range(3):
        record_task(_make_result(tmp_path), "default", TraceOptions())
    md_path = tmp_path / "report.md"
    export_report(md_path, limit=2)
    text = md_path.read_text(encoding="utf-8")
    assert text.startswith("# Bitmap Vector Studio History Report")
    assert "| task_id |" in text
    assert text.count("\n|") >= 3  # header + separator + at least one row


def test_export_report_unsupported_extension(tmp_path: Path):
    with pytest.raises(ValueError, match="Unsupported report format"):
        export_report(tmp_path / "report.txt", limit=10)


def test_graceful_corrupt_history(tmp_path: Path, monkeypatch):
    # Write a corrupt history file
    fake_history = tmp_path / "history.jsonl"
    fake_history.write_text("not json\n{\"valid\": true}\n", encoding="utf-8")
    monkeypatch.setattr(
        "vector_studio.history._history_path",
        lambda: fake_history,
    )
    records = get_recent_tasks(limit=100)
    assert len(records) == 1
    assert records[0]["valid"] is True


def test_graceful_missing_history():
    assert get_recent_tasks(limit=10) == []
    assert get_task("any-id") is None
    assert delete_task("any-id") is False
