from __future__ import annotations

import base64
import io
import json
import os
import threading
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# QR code is an optional dependency.
try:
    import qrcode
    from PIL import Image

    _HAS_QRCODE = True
except Exception:  # pragma: no cover
    _HAS_QRCODE = False

# Pillow is guaranteed (project dependency) and used for fallback QR generation.
from PIL import Image as PILImage, ImageDraw


# ---------------------------------------------------------------------------
# Abstract backend
# ---------------------------------------------------------------------------

class CloudBackend(ABC):
    """Abstract base class for cloud storage backends."""

    @abstractmethod
    def upload(self, file_path: Path, metadata: dict[str, Any]) -> str:
        """Upload a file and return a backend-specific file ID."""

    @abstractmethod
    def download(self, file_id: str, output_path: Path) -> Path:
        """Download a file by ID to *output_path* and return the path."""

    @abstractmethod
    def delete(self, file_id: str) -> bool:
        """Delete a file by ID. Returns True on success."""

    @abstractmethod
    def get_url(self, file_id: str) -> str:
        """Return a public share URL for the file."""

    def get_qr_code(self, file_id: str) -> bytes:
        """Generate a QR-code image (PNG) pointing to the file URL.

        If the ``qrcode`` package is installed it is used; otherwise a
        simple fallback image is generated via Pillow.
        """
        url = self.get_url(file_id)
        if _HAS_QRCODE:
            qr = qrcode.QRCode(version=1, box_size=10, border=2)
            qr.add_data(url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()

        # Fallback: generate a minimal text-based QR placeholder with Pillow.
        return _generate_fallback_qr(url)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_fallback_qr(url: str) -> bytes:
    """Create a simple PNG image containing the URL as text (fallback QR)."""
    # Create a small white image with the URL printed on it.
    lines = [url[i : i + 40] for i in range(0, len(url), 40)]
    height = max(100, 20 + len(lines) * 14)
    img = PILImage.new("RGB", (300, height), color="white")
    draw = ImageDraw.Draw(img)
    y = 10
    for line in lines:
        draw.text((10, y), line, fill="black")
        y += 14
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _http_json_request(
    url: str,
    method: str = "GET",
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """Perform an HTTP request and parse the JSON response."""
    req_headers = dict(headers or {})
    if method in ("POST", "PATCH") and data is not None:
        req_headers.setdefault("Content-Type", "application/json")
    req = Request(url, data=data, headers=req_headers, method=method)
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_request_bytes(
    url: str,
    method: str = "GET",
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
) -> bytes:
    """Perform an HTTP request and return raw bytes."""
    req = Request(url, data=data, headers=headers or {}, method=method)
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


# ---------------------------------------------------------------------------
# GitHub Gist backend
# ---------------------------------------------------------------------------

class GitHubGistBackend(CloudBackend):
    """Store SVG files as GitHub Gists.

    Parameters
    ----------
    token:
        GitHub personal access token. If ``None``, the environment variable
        ``GITHUB_TOKEN`` is read.
    public:
        Whether created gists should be public (``True``) or secret (``False``).
    """

    _API_BASE = "https://api.github.com"

    def __init__(self, token: str | None = None, public: bool = False) -> None:
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.public = public

    def _auth_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "BitmapVectorStudio/1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def upload(self, file_path: Path, metadata: dict[str, Any]) -> str:
        """Upload the SVG content to a new Gist and return the Gist ID."""
        content = file_path.read_text(encoding="utf-8")
        filename = metadata.get("filename", file_path.name)
        payload = {
            "description": metadata.get("description", "Shared SVG from Bitmap Vector Studio"),
            "public": self.public,
            "files": {filename: {"content": content}},
        }
        data = json.dumps(payload).encode("utf-8")
        try:
            resp = _http_json_request(
                f"{self._API_BASE}/gists",
                method="POST",
                data=data,
                headers=self._auth_headers(),
            )
        except HTTPError as exc:
            raise RuntimeError(f"GitHub Gist upload failed: {exc.code} {exc.reason}") from exc
        except URLError as exc:
            raise RuntimeError(f"GitHub Gist upload failed: {exc.reason}") from exc

        gist_id = resp.get("id")
        if not gist_id:
            raise RuntimeError("GitHub response did not contain a gist ID.")
        return gist_id

    def download(self, file_id: str, output_path: Path) -> Path:
        """Download the raw SVG from a Gist."""
        try:
            resp = _http_json_request(
                f"{self._API_BASE}/gists/{file_id}",
                headers=self._auth_headers(),
            )
        except HTTPError as exc:
            raise RuntimeError(f"GitHub Gist download failed: {exc.code} {exc.reason}") from exc
        except URLError as exc:
            raise RuntimeError(f"GitHub Gist download failed: {exc.reason}") from exc

        files = resp.get("files", {})
        if not files:
            raise RuntimeError("Gist contains no files.")
        # Pick the first file's raw URL.
        first_file = next(iter(files.values()))
        raw_url = first_file.get("raw_url")
        if not raw_url:
            raise RuntimeError("Gist file has no raw_url.")

        content = _http_request_bytes(raw_url, headers=self._auth_headers())
        output_path.write_bytes(content)
        return output_path

    def delete(self, file_id: str) -> bool:
        """Delete a Gist by ID."""
        try:
            req = Request(
                f"{self._API_BASE}/gists/{file_id}",
                headers=self._auth_headers(),
                method="DELETE",
            )
            with urlopen(req, timeout=30) as resp:
                # 204 No Content indicates success.
                return resp.status == 204
        except HTTPError as exc:
            if exc.code == 404:
                return False
            raise RuntimeError(f"GitHub Gist delete failed: {exc.code} {exc.reason}") from exc
        except URLError:
            return False

    def get_url(self, file_id: str) -> str:
        """Return the human-readable Gist URL."""
        return f"https://gist.github.com/{file_id}"


# ---------------------------------------------------------------------------
# Local server backend
# ---------------------------------------------------------------------------

class LocalServerBackend(CloudBackend):
    """Store shared files locally and serve them via the API server.

    Parameters
    ----------
    storage_dir:
        Directory where uploaded files are persisted.
    base_url:
        Public base URL of the API server (e.g. ``http://localhost:8000``).
    default_expire_hours:
        Default expiration time in hours.
    """

    def __init__(
        self,
        storage_dir: Path,
        base_url: str = "http://localhost:8000",
        default_expire_hours: int = 24,
    ) -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = base_url.rstrip("/")
        self.default_expire_hours = default_expire_hours
        self._meta_path = self.storage_dir / "_shares.json"
        self._lock = threading.Lock()
        self._shares: dict[str, dict[str, Any]] = {}
        self._load_shares()

    def _load_shares(self) -> None:
        """Load share registry from disk."""
        if self._meta_path.exists():
            try:
                data = json.loads(self._meta_path.read_text(encoding="utf-8"))
                self._shares = data if isinstance(data, dict) else {}
            except (json.JSONDecodeError, OSError):
                self._shares = {}
        else:
            self._shares = {}

    def _save_shares(self) -> None:
        """Persist share registry to disk."""
        with self._lock:
            try:
                self._meta_path.write_text(
                    json.dumps(self._shares, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
            except OSError:
                pass

    def _is_expired(self, share_id: str) -> bool:
        """Check whether a share has passed its expiration time."""
        meta = self._shares.get(share_id)
        if not meta:
            return True
        expire_at = meta.get("expire_at")
        if not expire_at:
            return False
        try:
            expire_dt = datetime.fromisoformat(expire_at)
            return datetime.now(timezone.utc) > expire_dt
        except ValueError:
            return False

    def _cleanup_expired(self) -> None:
        """Remove expired shares from the registry and disk."""
        expired = [sid for sid in self._shares if self._is_expired(sid)]
        for sid in expired:
            self._shares.pop(sid, None)
            file_path = self.storage_dir / sid
            if file_path.exists():
                try:
                    file_path.unlink()
                except OSError:
                    pass
        if expired:
            self._save_shares()

    def upload(self, file_path: Path, metadata: dict[str, Any]) -> str:
        """Copy the file into local storage and return a share ID."""
        self._cleanup_expired()
        share_id = metadata.get("share_id", str(uuid.uuid4()))
        dest = self.storage_dir / share_id
        try:
            dest.write_bytes(file_path.read_bytes())
        except OSError as exc:
            raise RuntimeError(f"Local upload failed: {exc}") from exc

        expire_hours = metadata.get("expire_hours", self.default_expire_hours)
        expire_at = datetime.now(timezone.utc) + timedelta(hours=expire_hours)
        self._shares[share_id] = {
            "filename": metadata.get("filename", file_path.name),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expire_at": expire_at.isoformat(),
            "content_type": metadata.get("content_type", "image/svg+xml"),
        }
        self._save_shares()
        return share_id

    def download(self, file_id: str, output_path: Path) -> Path:
        """Copy the locally stored file to *output_path*."""
        if self._is_expired(file_id):
            raise RuntimeError("Share has expired or does not exist.")
        src = self.storage_dir / file_id
        if not src.exists():
            raise RuntimeError("Share file not found.")
        output_path.write_bytes(src.read_bytes())
        return output_path

    def delete(self, file_id: str) -> bool:
        """Remove a local share."""
        meta = self._shares.pop(file_id, None)
        file_path = self.storage_dir / file_id
        if file_path.exists():
            try:
                file_path.unlink()
            except OSError:
                return False
        self._save_shares()
        return meta is not None or file_path.exists()

    def get_url(self, file_id: str) -> str:
        """Return the local API URL for the share."""
        return f"{self.base_url}/share/{file_id}"

    def list_shares(self) -> list[dict[str, Any]]:
        """Return metadata for all non-expired shares."""
        self._cleanup_expired()
        results: list[dict[str, Any]] = []
        for sid, meta in self._shares.items():
            entry = dict(meta)
            entry["share_id"] = sid
            entry["url"] = self.get_url(sid)
            results.append(entry)
        return results


# ---------------------------------------------------------------------------
# Cloud sync manager
# ---------------------------------------------------------------------------

class CloudSyncManager:
    """High-level manager for sharing SVG files via a cloud backend.

    Parameters
    ----------
    backend:
        A ``CloudBackend`` instance. When ``None`` a ``LocalServerBackend``
        using a temporary directory is created.
    """

    def __init__(self, backend: CloudBackend | None = None) -> None:
        if backend is None:
            import tempfile

            tmpdir = Path(tempfile.mkdtemp(prefix="vs-cloud-"))
            backend = LocalServerBackend(tmpdir)
        self.backend = backend
        self._registry: dict[str, dict[str, Any]] = {}

    def share_svg(self, svg_path: Path, expire_hours: int = 24) -> dict[str, Any]:
        """Upload an SVG and return share metadata including URL and QR code.

        Returns
        -------
        dict
            Keys: ``url``, ``qr_code`` (base64 PNG), ``expire_at`` (ISO),
            ``file_id``.
        """
        if not svg_path.exists():
            raise FileNotFoundError(f"SVG not found: {svg_path}")
        metadata = {
            "filename": svg_path.name,
            "expire_hours": expire_hours,
            "content_type": "image/svg+xml",
        }
        file_id = self.backend.upload(svg_path, metadata)
        url = self.backend.get_url(file_id)
        qr_bytes = self.backend.get_qr_code(file_id)
        qr_b64 = base64.b64encode(qr_bytes).decode("ascii")
        expire_at = (datetime.now(timezone.utc) + timedelta(hours=expire_hours)).isoformat()
        record = {
            "url": url,
            "qr_code": qr_b64,
            "expire_at": expire_at,
            "file_id": file_id,
        }
        self._registry[file_id] = record
        return record

    def share_batch(self, svg_paths: list[Path]) -> list[dict[str, Any]]:
        """Share multiple SVGs and return a list of share metadata dicts."""
        results: list[dict[str, Any]] = []
        for path in svg_paths:
            try:
                results.append(self.share_svg(path))
            except Exception as exc:
                results.append({"file": str(path), "error": str(exc)})
        return results

    def get_shared_files(self) -> list[dict[str, Any]]:
        """List all shares tracked by this manager."""
        if isinstance(self.backend, LocalServerBackend):
            return self.backend.list_shares()
        return [dict(r) for r in self._registry.values()]

    def revoke_share(self, file_id: str) -> bool:
        """Revoke a share by file ID."""
        success = self.backend.delete(file_id)
        self._registry.pop(file_id, None)
        return success
