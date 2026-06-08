from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any


class VectorStudioClient:
    """Python client SDK for the Bitmap Vector Studio API.

    Uses only the Python standard library (``urllib``) so it has zero
    external dependencies beyond the Python runtime.
    """

    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        self.base_url = base_url.rstrip("/")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, bytes]:
        """Send an HTTP request and return *(status, body)*."""
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, method=method)
        if headers:
            for key, value in headers.items():
                req.add_header(key, value)
        if data is not None:
            req.data = data
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read()

    def _multipart_request(
        self,
        path: str,
        fields: dict[str, str],
        files: dict[str, Path],
    ) -> tuple[int, bytes]:
        """Build and send a ``multipart/form-data`` request using urllib."""
        boundary = "----VectorStudioBoundary7f8a9b2c"
        body = bytearray()

        for name, value in fields.items():
            body.extend(f"--{boundary}\r\n".encode())
            body.extend(f'Content-Disposition: form-data; name="{name}"\r\n'.encode())
            body.extend(b"\r\n")
            body.extend(value.encode())
            body.extend(b"\r\n")

        for name, path in files.items():
            suffix = path.suffix.lower()
            mime = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".webp": "image/webp",
                ".bmp": "image/bmp",
                ".tif": "image/tiff",
                ".tiff": "image/tiff",
            }.get(suffix, "application/octet-stream")
            data = path.read_bytes()
            body.extend(f"--{boundary}\r\n".encode())
            body.extend(
                f'Content-Disposition: form-data; name="{name}"; filename="{path.name}"\r\n'.encode()
            )
            body.extend(f"Content-Type: {mime}\r\n".encode())
            body.extend(b"\r\n")
            body.extend(data)
            body.extend(b"\r\n")

        body.extend(f"--{boundary}--\r\n".encode())

        headers = {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }
        return self._request("POST", path, data=bytes(body), headers=headers)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def convert(self, image_path: Path, preset: str = "poster", options: dict[str, Any] | None = None) -> bytes:
        """Upload an image and retrieve the converted SVG as bytes.

        Args:
            image_path: Path to the raster image file.
            preset: Tracing preset name (e.g. ``"poster"``, ``"logo"``).
            options: Optional dictionary of VTracer option overrides.

        Returns:
            Raw SVG bytes.

        Raises:
            urllib.error.HTTPError: If the server returns an error status.
        """
        image_path = Path(image_path)
        fields = {"preset": preset}
        if options:
            fields["options"] = json.dumps(options)
        status, body = self._multipart_request("/convert", fields, {"file": image_path})
        if status != 200:
            raise urllib.error.HTTPError(
                f"{self.base_url}/convert", status, body.decode("utf-8", errors="replace"), None, None
            )
        return body

    def convert_async(self, image_path: Path, preset: str = "poster", options: dict[str, Any] | None = None) -> str:
        """Start an asynchronous conversion and return the task ID.

        Args:
            image_path: Path to the raster image file.
            preset: Tracing preset name.
            options: Optional dictionary of VTracer option overrides.

        Returns:
            The task ID string.
        """
        image_path = Path(image_path)
        fields = {"preset": preset}
        if options:
            fields["options"] = json.dumps(options)
        status, body = self._multipart_request("/convert/async", fields, {"file": image_path})
        if status != 200:
            raise urllib.error.HTTPError(
                f"{self.base_url}/convert/async", status, body.decode("utf-8", errors="replace"), None, None
            )
        data = json.loads(body)
        return data["task_id"]

    def get_status(self, task_id: str) -> dict[str, Any]:
        """Query the status of an asynchronous task.

        Args:
            task_id: The task ID returned by :meth:`convert_async`.

        Returns:
            Status dictionary.
        """
        status, body = self._request("GET", f"/status/{task_id}")
        if status != 200:
            raise urllib.error.HTTPError(
                f"{self.base_url}/status/{task_id}", status, body.decode("utf-8", errors="replace"), None, None
            )
        return json.loads(body)

    def download(self, task_id: str, format: str = "svg") -> bytes:
        """Download the result of a completed task.

        Args:
            task_id: The task ID.
            format: Desired format – ``"svg"``, ``"pdf"`` or ``"png"``.

        Returns:
            Raw file bytes.
        """
        status, body = self._request("GET", f"/download/{task_id}/{format}")
        if status != 200:
            raise urllib.error.HTTPError(
                f"{self.base_url}/download/{task_id}/{format}",
                status,
                body.decode("utf-8", errors="replace"),
                None,
                None,
            )
        return body

    def recommend(self, image_path: Path) -> dict[str, Any]:
        """Analyze an image and get a preset recommendation.

        Args:
            image_path: Path to the raster image file.

        Returns:
            Recommendation dictionary with keys ``preset``, ``confidence``,
            ``reason``, and ``features``.
        """
        image_path = Path(image_path)
        status, body = self._multipart_request("/recommend", {}, {"file": image_path})
        if status != 200:
            raise urllib.error.HTTPError(
                f"{self.base_url}/recommend", status, body.decode("utf-8", errors="replace"), None, None
            )
        return json.loads(body)

    def batch_convert(self, image_paths: list[Path], preset: str = "poster", options: dict[str, Any] | None = None) -> list[str]:
        """Batch-convert multiple images asynchronously.

        Args:
            image_paths: List of paths to raster image files.
            preset: Tracing preset name.
            options: Optional dictionary of VTracer option overrides.

        Returns:
            List of task IDs.
        """
        fields = {"preset": preset}
        if options:
            fields["options"] = json.dumps(options)
        files = {f"files": Path(p) for p in image_paths}
        status, body = self._multipart_request("/batch", fields, files)
        if status != 200:
            raise urllib.error.HTTPError(
                f"{self.base_url}/batch", status, body.decode("utf-8", errors="replace"), None, None
            )
        data = json.loads(body)
        return data["task_ids"]

    def health(self) -> dict[str, str]:
        """Check API health.

        Returns:
            Health dictionary with ``status`` and ``version``.
        """
        status, body = self._request("GET", "/health")
        if status != 200:
            raise urllib.error.HTTPError(
                f"{self.base_url}/health", status, body.decode("utf-8", errors="replace"), None, None
            )
        return json.loads(body)
