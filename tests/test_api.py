from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from vector_studio.api import app, _cleanup_api_temp, _get_queue
from vector_studio.models import TraceOptions, TraceResult

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    """Reset global queue and temp directory between tests."""
    import vector_studio.api as api_module

    api_module._task_queue = None
    yield
    api_module._cleanup_api_temp()
    api_module._task_queue = None


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestPresetsEndpoint:
    def test_presets_lists_all(self):
        response = client.get("/presets")
        assert response.status_code == 200
        data = response.json()
        names = {p["name"] for p in data}
        assert "poster" in names
        assert "bw" in names
        assert "photo" in names
        assert "logo" in names


class TestConvertEndpoint:
    def test_convert_sync_success(self, tmp_path: Path):
        img = tmp_path / "test.png"
        img.write_bytes(b"fake png data")

        svg = tmp_path / "out.svg"
        svg.write_text("<svg></svg>")

        mock_result = TraceResult(
            input_path=img,
            svg_path=svg,
            engine="python-vtracer",
            elapsed_seconds=0.5,
            stats={"paths": 3},
        )

        with patch("vector_studio.api.trace_image", return_value=mock_result):
            with img.open("rb") as f:
                response = client.post(
                    "/convert",
                    files={"file": ("test.png", f, "image/png")},
                    data={"preset": "poster", "options": "{}"},
                )

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/svg+xml"
        assert response.content == b"<svg></svg>"

    def test_convert_sync_bad_preset(self, tmp_path: Path):
        img = tmp_path / "test.png"
        img.write_bytes(b"fake png data")

        with img.open("rb") as f:
            response = client.post(
                "/convert",
                files={"file": ("test.png", f, "image/png")},
                data={"preset": "nonexistent"},
            )

        assert response.status_code == 400
        assert "Unknown preset" in response.json()["detail"]

    def test_convert_sync_unsupported_format(self, tmp_path: Path):
        txt = tmp_path / "test.txt"
        txt.write_text("not an image")

        with txt.open("rb") as f:
            response = client.post(
                "/convert",
                files={"file": ("test.txt", f, "text/plain")},
            )

        assert response.status_code == 400
        assert "Unsupported input format" in response.json()["detail"]

    def test_convert_sync_bad_options_json(self, tmp_path: Path):
        img = tmp_path / "test.png"
        img.write_bytes(b"fake png data")

        with img.open("rb") as f:
            response = client.post(
                "/convert",
                files={"file": ("test.png", f, "image/png")},
                data={"options": "not-json"},
            )

        assert response.status_code == 400
        assert "Invalid options JSON" in response.json()["detail"]


class TestAsyncConvertEndpoint:
    def test_convert_async_returns_task_id(self, tmp_path: Path):
        img = tmp_path / "test.png"
        img.write_bytes(b"fake png data")

        with img.open("rb") as f:
            response = client.post(
                "/convert/async",
                files={"file": ("test.png", f, "image/png")},
                data={"preset": "logo"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "pending"

    def test_status_unknown_task(self):
        response = client.get("/status/does-not-exist")
        assert response.status_code == 404
        assert "Task not found" in response.json()["detail"]

    def test_download_not_completed(self, tmp_path: Path):
        q = _get_queue()
        with patch.object(q, "get_status", return_value={
            "task_id": "test-123",
            "status": "pending",
            "progress": 0.0,
            "result": None,
            "error": None,
            "created_at": "2024-01-01T00:00:00",
            "started_at": None,
            "completed_at": None,
        }):
            response = client.get("/download/test-123/svg")

        assert response.status_code == 400
        assert "not completed" in response.json()["detail"]


class TestRecommendEndpoint:
    def test_recommend_returns_preset(self, tmp_path: Path):
        img = tmp_path / "test.png"
        img.write_bytes(b"fake png data")

        with patch(
            "vector_studio.api.recommend_for_image",
            return_value=("logo", 0.92, "Logo candidate", {"color_count": 3}),
        ):
            with img.open("rb") as f:
                response = client.post(
                    "/recommend",
                    files={"file": ("test.png", f, "image/png")},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["preset"] == "logo"
        assert data["confidence"] == 0.92
        assert data["reason"] == "Logo candidate"
        assert "features" in data

    def test_recommend_unsupported_format(self, tmp_path: Path):
        txt = tmp_path / "test.txt"
        txt.write_text("not an image")

        with txt.open("rb") as f:
            response = client.post(
                "/recommend",
                files={"file": ("test.txt", f, "text/plain")},
            )

        assert response.status_code == 400
        assert "Unsupported input format" in response.json()["detail"]


class TestBatchEndpoint:
    def test_batch_returns_task_ids(self, tmp_path: Path):
        img1 = tmp_path / "a.png"
        img1.write_bytes(b"fake1")
        img2 = tmp_path / "b.png"
        img2.write_bytes(b"fake2")

        with img1.open("rb") as f1, img2.open("rb") as f2:
            response = client.post(
                "/batch",
                files=[
                    ("files", ("a.png", f1, "image/png")),
                    ("files", ("b.png", f2, "image/png")),
                ],
                data={"preset": "bw"},
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["task_ids"]) == 2

    def test_batch_bad_preset(self, tmp_path: Path):
        img = tmp_path / "a.png"
        img.write_bytes(b"fake")

        with img.open("rb") as f:
            response = client.post(
                "/batch",
                files=[("files", ("a.png", f, "image/png"))],
                data={"preset": "bad_preset"},
            )

        assert response.status_code == 400
        assert "Unknown preset" in response.json()["detail"]


class TestDownloadEndpoint:
    def test_download_svg(self, tmp_path: Path):
        svg = tmp_path / "result.svg"
        svg.write_text("<svg></svg>")

        q = _get_queue()
        with patch.object(
            q,
            "get_status",
            return_value={
                "task_id": "test-123",
                "status": "completed",
                "progress": 100.0,
                "result": {"svg_path": str(svg), "elapsed_seconds": 1.0, "stats": {}},
                "error": None,
                "created_at": "2024-01-01T00:00:00",
                "started_at": "2024-01-01T00:00:01",
                "completed_at": "2024-01-01T00:00:02",
            },
        ):
            response = client.get("/download/test-123/svg")

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/svg+xml"
        assert response.content == b"<svg></svg>"

    def test_download_unknown_task(self):
        response = client.get("/download/unknown-id/svg")
        assert response.status_code == 404
        assert "Task not found" in response.json()["detail"]

    def test_download_bad_format(self, tmp_path: Path):
        svg = tmp_path / "result.svg"
        svg.write_text("<svg></svg>")

        q = _get_queue()
        with patch.object(
            q,
            "get_status",
            return_value={
                "task_id": "test-123",
                "status": "completed",
                "progress": 100.0,
                "result": {"svg_path": str(svg), "elapsed_seconds": 1.0, "stats": {}},
                "error": None,
                "created_at": "2024-01-01T00:00:00",
                "started_at": None,
                "completed_at": None,
            },
        ):
            response = client.get("/download/test-123/eps")

        assert response.status_code == 400
        assert "Format must be one of" in response.json()["detail"]
