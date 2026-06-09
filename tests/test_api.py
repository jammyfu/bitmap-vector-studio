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
        assert data["status"] == "healthy"
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


class TestShareEndpoints:
    def test_share_svg_success(self, tmp_path: Path):
        svg = tmp_path / "test.svg"
        svg.write_text("<svg></svg>")
        with patch("vector_studio.api._get_share_manager") as mock_mgr:
            mock_mgr.return_value.share_svg.return_value = {
                "url": "http://localhost:8000/share/abc",
                "file_id": "abc",
                "expire_at": "2025-01-01T00:00:00",
                "qr_code": "base64data",
            }
            with svg.open("rb") as f:
                response = client.post("/share", files={"file": ("test.svg", f, "image/svg+xml")})
        assert response.status_code == 200
        data = response.json()
        assert data["file_id"] == "abc"

    def test_share_non_svg_rejected(self, tmp_path: Path):
        png = tmp_path / "test.png"
        png.write_bytes(b"fake png")
        with png.open("rb") as f:
            response = client.post("/share", files={"file": ("test.png", f, "image/png")})
        assert response.status_code == 400
        assert "Only SVG files" in response.json()["detail"]

    def test_get_shared_svg_local(self, tmp_path: Path):
        from vector_studio.cloud_sync import LocalServerBackend
        from datetime import datetime, timezone, timedelta
        backend = LocalServerBackend(storage_dir=tmp_path, base_url="http://localhost:8000")
        backend._shares["abc"] = {"filename": "test.svg", "content_type": "image/svg+xml", "expire_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()}
        (tmp_path / "abc").write_text("<svg></svg>")
        with patch("vector_studio.api._get_share_manager") as mock_mgr:
            mock_mgr.return_value.backend = backend
            response = client.get("/share/abc")
        assert response.status_code == 200
        assert response.content == b"<svg></svg>"

    def test_get_shared_svg_expired(self, tmp_path: Path):
        from vector_studio.cloud_sync import LocalServerBackend
        from datetime import datetime, timezone, timedelta
        backend = LocalServerBackend(storage_dir=tmp_path, base_url="http://localhost:8000")
        backend._shares["abc"] = {"filename": "test.svg", "content_type": "image/svg+xml", "expire_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()}
        (tmp_path / "abc").write_text("<svg></svg>")
        with patch("vector_studio.api._get_share_manager") as mock_mgr:
            mock_mgr.return_value.backend = backend
            response = client.get("/share/abc")
        assert response.status_code == 404
        assert "expired" in response.json()["detail"].lower()

    def test_revoke_share(self, tmp_path: Path):
        with patch("vector_studio.api._get_share_manager") as mock_mgr:
            mock_mgr.return_value.revoke_share.return_value = True
            response = client.delete("/share/abc")
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_revoke_share_not_found(self, tmp_path: Path):
        with patch("vector_studio.api._get_share_manager") as mock_mgr:
            mock_mgr.return_value.revoke_share.return_value = False
            response = client.delete("/share/abc")
        assert response.status_code == 404

    def test_list_shares(self, tmp_path: Path):
        with patch("vector_studio.api._get_share_manager") as mock_mgr:
            mock_mgr.return_value.get_shared_files.return_value = [{"share_id": "abc", "url": "http://localhost/abc"}]
            response = client.get("/shares")
        assert response.status_code == 200
        assert len(response.json()["shares"]) == 1

    def test_get_share_qr(self, tmp_path: Path):
        from vector_studio.cloud_sync import LocalServerBackend
        from datetime import datetime, timezone, timedelta
        backend = LocalServerBackend(storage_dir=tmp_path, base_url="http://localhost:8000")
        backend._shares["abc"] = {"expire_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()}
        with patch("vector_studio.api._get_share_manager") as mock_mgr:
            mock_mgr.return_value.backend = backend
            with patch.object(backend, "get_qr_code", return_value=b"pngdata"):
                response = client.get("/share/abc/qr")
        assert response.status_code == 200
        assert "qr_code" in response.json()


class TestDownloadPdfPng:
    def test_download_pdf(self, tmp_path: Path):
        svg = tmp_path / "result.svg"
        svg.write_text("<svg></svg>")
        pdf = tmp_path / "result.pdf"
        pdf.write_bytes(b"pdfdata")

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
            with patch("vector_studio.api.export_svg_to_pdf", return_value=pdf):
                response = client.get("/download/test-123/pdf")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"

    def test_download_png(self, tmp_path: Path):
        svg = tmp_path / "result.svg"
        svg.write_text("<svg></svg>")
        png = tmp_path / "result.png"
        png.write_bytes(b"pngdata")

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
            with patch("vector_studio.api.export_svg_to_png", return_value=png):
                response = client.get("/download/test-123/png")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"

    def test_download_pdf_export_failure(self, tmp_path: Path):
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
            with patch("vector_studio.api.export_svg_to_pdf", side_effect=RuntimeError("no cairosvg")):
                response = client.get("/download/test-123/pdf")
        assert response.status_code == 500
        assert "PDF export failed" in response.json()["detail"]


class TestAsyncConvertMore:
    def test_convert_async_bad_preset(self, tmp_path: Path):
        img = tmp_path / "test.png"
        img.write_bytes(b"fake png data")
        with img.open("rb") as f:
            response = client.post(
                "/convert/async",
                files={"file": ("test.png", f, "image/png")},
                data={"preset": "nonexistent"},
            )
        assert response.status_code == 400
        assert "Unknown preset" in response.json()["detail"]

    def test_convert_async_unsupported_format(self, tmp_path: Path):
        txt = tmp_path / "test.txt"
        txt.write_text("not an image")
        with txt.open("rb") as f:
            response = client.post(
                "/convert/async",
                files={"file": ("test.txt", f, "text/plain")},
            )
        assert response.status_code == 400
        assert "Unsupported input format" in response.json()["detail"]


class TestShareEndpointsMore:
    def test_share_missing_file(self):
        response = client.post("/share")
        assert response.status_code == 422

    def test_share_qr_not_found(self):
        from vector_studio.cloud_sync import LocalServerBackend
        from datetime import datetime, timezone, timedelta
        import tempfile
        tmpdir = Path(tempfile.mkdtemp())
        backend = LocalServerBackend(storage_dir=tmpdir, base_url="http://localhost:8000")
        # Do NOT add "abc" to shares so it returns 404
        with patch("vector_studio.api._get_share_manager") as mock_mgr:
            mock_mgr.return_value.backend = backend
            response = client.get("/share/abc/qr")
        assert response.status_code == 404

    def test_share_with_custom_expire(self, tmp_path: Path):
        svg = tmp_path / "test.svg"
        svg.write_text("<svg></svg>")
        with patch("vector_studio.api._get_share_manager") as mock_mgr:
            mock_mgr.return_value.share_svg.return_value = {
                "url": "http://localhost:8000/share/abc",
                "file_id": "abc",
                "expire_at": "2025-01-01T00:00:00",
                "qr_code": "base64data",
            }
            with svg.open("rb") as f:
                response = client.post("/share?expire_hours=48", files={"file": ("test.svg", f, "image/svg+xml")})
        assert response.status_code == 200
        assert response.json()["file_id"] == "abc"


class TestApiHealthMore:
    def test_health_returns_version(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert data["status"] == "healthy"


class TestApiConvertMore:
    def test_convert_with_custom_options(self, tmp_path: Path):
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
                    data={"preset": "logo", "options": '{"filter_speckle": 2}'},
                )
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/svg+xml"

    def test_convert_with_empty_options(self, tmp_path: Path):
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


class TestFarmEndpoints:
    def test_farm_status_empty(self):
        response = client.get("/farm/status")
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["total_workers"] == 0
        assert data["summary"]["total_tasks"] == 0

    def test_farm_register_worker(self):
        response = client.post(
            "/farm/workers/register",
            json={"worker_id": "w1", "host": "127.0.0.1", "port": 9000, "capacity": 4},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["worker_id"] == "w1"

    def test_farm_list_workers(self):
        client.post(
            "/farm/workers/register",
            json={"worker_id": "w2", "host": "127.0.0.1", "port": 9001, "capacity": 2},
        )
        response = client.get("/farm/workers")
        assert response.status_code == 200
        data = response.json()
        assert any(w["worker_id"] == "w2" for w in data["workers"])

    def test_farm_heartbeat(self):
        client.post(
            "/farm/workers/register",
            json={"worker_id": "w3", "host": "127.0.0.1", "port": 9002, "capacity": 2},
        )
        response = client.post("/farm/workers/w3/heartbeat")
        assert response.status_code == 200
        assert response.json()["ok"] is True

    def test_farm_heartbeat_unknown_worker(self):
        response = client.post("/farm/workers/unknown/heartbeat")
        assert response.status_code == 404

    def test_farm_submit_task(self, tmp_path: Path):
        img = tmp_path / "test.png"
        img.write_bytes(b"fake png data")
        with img.open("rb") as f:
            response = client.post(
                "/farm/submit",
                files={"file": ("test.png", f, "image/png")},
                data={"preset": "poster", "options": "{}", "priority": "5"},
            )
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "pending"

    def test_farm_task_status(self, tmp_path: Path):
        img = tmp_path / "test.png"
        img.write_bytes(b"fake png data")
        with img.open("rb") as f:
            resp = client.post(
                "/farm/submit",
                files={"file": ("test.png", f, "image/png")},
                data={"preset": "poster"},
            )
        task_id = resp.json()["task_id"]
        response = client.get(f"/farm/status/{task_id}")
        assert response.status_code == 200
        assert response.json()["task_id"] == task_id

    def test_farm_task_status_unknown(self):
        response = client.get("/farm/status/does-not-exist")
        assert response.status_code == 404
