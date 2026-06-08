from __future__ import annotations

import base64
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest

from vector_studio.cloud_sync import (
    CloudSyncManager,
    GitHubGistBackend,
    LocalServerBackend,
    _generate_fallback_qr,
    _http_json_request,
)


class TestGenerateFallbackQr:
    def test_fallback_qr_returns_png_bytes(self):
        """Fallback QR generation must return valid PNG bytes."""
        data = _generate_fallback_qr("https://example.com/test")
        assert isinstance(data, bytes)
        assert len(data) > 0
        # PNG magic bytes
        assert data[:8] == b"\x89PNG\r\n\x1a\n"


class TestLocalServerBackend:
    def test_upload_creates_share(self, tmp_path: Path):
        """Uploading a file must create a share ID and persist metadata."""
        backend = LocalServerBackend(storage_dir=tmp_path, base_url="http://localhost:8000")
        svg = tmp_path / "test.svg"
        svg.write_text("<svg></svg>")
        share_id = backend.upload(svg, {"filename": "test.svg", "expire_hours": 1})
        assert share_id is not None
        assert (tmp_path / share_id).exists()
        assert share_id in backend._shares

    def test_download_roundtrip(self, tmp_path: Path):
        """Download must return the original file content."""
        backend = LocalServerBackend(storage_dir=tmp_path, base_url="http://localhost:8000")
        svg = tmp_path / "original.svg"
        svg.write_text("<svg><circle/></svg>")
        share_id = backend.upload(svg, {})
        out = tmp_path / "downloaded.svg"
        backend.download(share_id, out)
        assert out.read_text() == "<svg><circle/></svg>"

    def test_delete_removes_file_and_meta(self, tmp_path: Path):
        """Delete must remove the file and metadata."""
        backend = LocalServerBackend(storage_dir=tmp_path, base_url="http://localhost:8000")
        svg = tmp_path / "del.svg"
        svg.write_text("<svg></svg>")
        share_id = backend.upload(svg, {})
        assert backend.delete(share_id) is True
        assert not (tmp_path / share_id).exists()
        assert share_id not in backend._shares

    def test_expired_share_is_inaccessible(self, tmp_path: Path):
        """An expired share must be treated as missing."""
        backend = LocalServerBackend(storage_dir=tmp_path, base_url="http://localhost:8000")
        svg = tmp_path / "exp.svg"
        svg.write_text("<svg></svg>")
        share_id = backend.upload(svg, {"expire_hours": -1})
        assert backend._is_expired(share_id) is True
        out = tmp_path / "out.svg"
        with pytest.raises(RuntimeError, match="expired"):
            backend.download(share_id, out)

    def test_list_shares_filters_expired(self, tmp_path: Path):
        """list_shares must not include expired entries."""
        backend = LocalServerBackend(storage_dir=tmp_path, base_url="http://localhost:8000")
        svg = tmp_path / "a.svg"
        svg.write_text("<svg></svg>")
        backend.upload(svg, {"expire_hours": -1})
        active = backend.list_shares()
        assert len(active) == 0

    def test_get_url_format(self, tmp_path: Path):
        """get_url must return the expected local API URL."""
        backend = LocalServerBackend(storage_dir=tmp_path, base_url="http://localhost:8000")
        url = backend.get_url("abc-123")
        assert url == "http://localhost:8000/share/abc-123"


class TestGitHubGistBackend:
    def test_upload_success(self, tmp_path: Path):
        """Upload must return a gist ID when GitHub responds correctly."""
        backend = GitHubGistBackend(token="fake-token")
        svg = tmp_path / "gh.svg"
        svg.write_text("<svg></svg>")
        mock_resp = {"id": "gist-12345"}
        with patch("vector_studio.cloud_sync._http_json_request", return_value=mock_resp):
            gid = backend.upload(svg, {"description": "Test share"})
        assert gid == "gist-12345"

    def test_upload_failure_raises(self, tmp_path: Path):
        """Upload must raise RuntimeError when GitHub returns an error."""
        backend = GitHubGistBackend(token="fake-token")
        svg = tmp_path / "gh.svg"
        svg.write_text("<svg></svg>")
        err = HTTPError("https://api.github.com/gists", 422, "Unprocessable", {}, None)  # type: ignore[arg-type]
        with patch("vector_studio.cloud_sync._http_json_request", side_effect=err):
            with pytest.raises(RuntimeError, match="GitHub Gist upload failed"):
                backend.upload(svg, {})

    def test_download_success(self, tmp_path: Path):
        """Download must write the raw gist content to the output path."""
        backend = GitHubGistBackend(token="fake-token")
        out = tmp_path / "downloaded.svg"
        gist_meta = {
            "files": {"gh.svg": {"raw_url": "https://gist.githubusercontent.com/raw/gh.svg"}}
        }
        with patch("vector_studio.cloud_sync._http_json_request", return_value=gist_meta):
            with patch("vector_studio.cloud_sync._http_request_bytes", return_value=b"<svg>raw</svg>"):
                backend.download("gist-123", out)
        assert out.read_text() == "<svg>raw</svg>"

    def test_delete_success(self):
        """Delete must return True when GitHub responds with 204."""
        backend = GitHubGistBackend(token="fake-token")
        mock_resp = MagicMock()
        mock_resp.status = 204
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("vector_studio.cloud_sync.urlopen", return_value=mock_resp):
            assert backend.delete("gist-123") is True

    def test_delete_not_found(self):
        """Delete must return False when the gist does not exist."""
        backend = GitHubGistBackend(token="fake-token")
        err = HTTPError("https://api.github.com/gists/gist-123", 404, "Not Found", {}, None)  # type: ignore[arg-type]
        with patch("vector_studio.cloud_sync.urlopen", side_effect=err):
            assert backend.delete("gist-123") is False

    def test_get_url_format(self):
        """get_url must return the human-readable gist URL."""
        backend = GitHubGistBackend()
        assert backend.get_url("gist-123") == "https://gist.github.com/gist-123"


class TestCloudSyncManager:
    def test_share_svg_returns_expected_keys(self, tmp_path: Path):
        """share_svg must return a dict with url, qr_code, expire_at, file_id."""
        backend = LocalServerBackend(storage_dir=tmp_path, base_url="http://localhost:8000")
        manager = CloudSyncManager(backend=backend)
        svg = tmp_path / "share.svg"
        svg.write_text("<svg></svg>")
        result = manager.share_svg(svg, expire_hours=1)
        assert set(result.keys()) == {"url", "qr_code", "expire_at", "file_id"}
        assert result["url"].startswith("http://localhost:8000/share/")
        # qr_code is base64
        decoded = base64.b64decode(result["qr_code"])
        assert decoded[:8] == b"\x89PNG\r\n\x1a\n"

    def test_share_batch(self, tmp_path: Path):
        """share_batch must process multiple files and return results."""
        backend = LocalServerBackend(storage_dir=tmp_path, base_url="http://localhost:8000")
        manager = CloudSyncManager(backend=backend)
        svg1 = tmp_path / "a.svg"
        svg1.write_text("<svg>A</svg>")
        svg2 = tmp_path / "b.svg"
        svg2.write_text("<svg>B</svg>")
        results = manager.share_batch([svg1, svg2])
        assert len(results) == 2
        assert "url" in results[0]
        assert "url" in results[1]

    def test_get_shared_files(self, tmp_path: Path):
        """get_shared_files must list active shares."""
        backend = LocalServerBackend(storage_dir=tmp_path, base_url="http://localhost:8000")
        manager = CloudSyncManager(backend=backend)
        svg = tmp_path / "list.svg"
        svg.write_text("<svg></svg>")
        manager.share_svg(svg, expire_hours=1)
        shares = manager.get_shared_files()
        assert len(shares) >= 1

    def test_revoke_share(self, tmp_path: Path):
        """revoke_share must remove the share and return True."""
        backend = LocalServerBackend(storage_dir=tmp_path, base_url="http://localhost:8000")
        manager = CloudSyncManager(backend=backend)
        svg = tmp_path / "revoke.svg"
        svg.write_text("<svg></svg>")
        result = manager.share_svg(svg, expire_hours=1)
        fid = result["file_id"]
        assert manager.revoke_share(fid) is True
        assert manager.revoke_share(fid) is False

    def test_share_missing_file_raises(self, tmp_path: Path):
        """share_svg must raise FileNotFoundError for a missing file."""
        backend = LocalServerBackend(storage_dir=tmp_path, base_url="http://localhost:8000")
        manager = CloudSyncManager(backend=backend)
        with pytest.raises(FileNotFoundError):
            manager.share_svg(tmp_path / "missing.svg")


class TestHttpJsonRequest:
    def test_http_json_request_parses_response(self):
        """_http_json_request must parse a JSON response correctly."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"ok": true}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("vector_studio.cloud_sync.urlopen", return_value=mock_resp):
            result = _http_json_request("https://example.com/api")
        assert result == {"ok": True}
