from __future__ import annotations

import base64
import json
import logging
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import preset_manager as pm
from .config import _default_config_path, _has_yaml, _load_json, _load_yaml
from .models import TraceOptions

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default market sources (placeholders)
# ---------------------------------------------------------------------------

OFFICIAL_GIST_ID: str = "bitmap-vector-studio-official-examples"
"""Placeholder gist ID for the official example preset collection."""

COMMUNITY_REPO_OWNER: str = "bitmap-vector-studio"
"""Placeholder repository owner for the community preset repo."""

COMMUNITY_REPO_NAME: str = "community-presets"
"""Placeholder repository name for the community preset repo."""

COMMUNITY_REPO_PATH: str = "presets"
"""Default subdirectory inside the community repo where presets live."""


# ---------------------------------------------------------------------------
# Local market data helpers
# ---------------------------------------------------------------------------

def _market_data_dir() -> Path:
    """Return the directory used for market data (ratings, cache)."""
    directory = Path.home() / ".bitmap_vector_studio" / "market"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _ratings_file() -> Path:
    """Return the path to the local ratings file."""
    return _market_data_dir() / "ratings.json"


def _load_ratings() -> dict[str, dict[str, Any]]:
    """Load local ratings from disk.

    Returns an empty dict when the file does not exist or is unreadable.
    """
    path = _ratings_file()
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def _save_ratings(data: dict[str, dict[str, Any]]) -> None:
    """Persist local ratings to disk atomically."""
    path = _ratings_file()
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    tmp.replace(path)


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def _http_json(
    url: str,
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    method: str | None = None,
    timeout: float = 10.0,
) -> Any:
    """Perform an HTTP request and return parsed JSON.

    Args:
        url: Target URL.
        headers: Optional request headers.
        data: Optional request body bytes.
        method: HTTP method (defaults to GET unless *data* is provided).
        timeout: Socket timeout in seconds.

    Raises:
        urllib.error.HTTPError: On HTTP error responses.
        urllib.error.URLError: On network-level failures.
        TimeoutError: When the request exceeds *timeout*.
        json.JSONDecodeError: When the response is not valid JSON.
    """
    req = urllib.request.Request(url, data=data, method=method)
    if headers:
        for key, value in headers.items():
            req.add_header(key, value)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------

class MarketBackend(ABC):
    """Abstract base class for preset market backends."""

    @abstractmethod
    def list_presets(self) -> list[dict]:
        """List available presets from the market.

        Returns:
            A list of preset dictionaries.
        """

    @abstractmethod
    def search_presets(self, query: str) -> list[dict]:
        """Search presets by query string.

        Args:
            query: Search query.

        Returns:
            A list of matching preset dictionaries.
        """

    @abstractmethod
    def download_preset(self, preset_id: str) -> dict:
        """Download a specific preset by ID.

        Args:
            preset_id: The preset identifier.

        Returns:
            The preset dictionary.

        Raises:
            ValueError: If the preset is not found or contains invalid data.
        """

    @abstractmethod
    def upload_preset(self, preset_data: dict, auth_token: str | None = None) -> str:
        """Upload a preset to the market.

        Args:
            preset_data: The preset dictionary to upload.
            auth_token: Optional authentication token.

        Returns:
            The ID of the uploaded preset.

        Raises:
            RuntimeError: If the upload fails.
        """


class MultiBackend(MarketBackend):
    """Combine multiple backends into a single logical backend."""

    def __init__(self, backends: list[MarketBackend]) -> None:
        """Initialize with a list of backends.

        Args:
            backends: Backends to query in order.
        """
        self.backends = backends

    def list_presets(self) -> list[dict]:
        """Aggregate presets from all backends."""
        all_presets: list[dict] = []
        for backend in self.backends:
            try:
                all_presets.extend(backend.list_presets())
            except Exception as exc:
                logger.warning("%s.list_presets failed: %s", type(backend).__name__, exc)
        return all_presets

    def search_presets(self, query: str) -> list[dict]:
        """Aggregate search results from all backends and deduplicate."""
        all_presets: list[dict] = []
        for backend in self.backends:
            try:
                all_presets.extend(backend.search_presets(query))
            except Exception as exc:
                logger.warning("%s.search_presets failed: %s", type(backend).__name__, exc)
        seen: set[str] = set()
        result: list[dict] = []
        for preset in all_presets:
            pid = preset.get("id")
            if pid and pid not in seen:
                seen.add(pid)
                result.append(preset)
        return result

    def download_preset(self, preset_id: str) -> dict:
        """Try each backend until the preset is found."""
        for backend in self.backends:
            try:
                return backend.download_preset(preset_id)
            except Exception:
                continue
        raise ValueError(f"Preset {preset_id} not found in any backend.")

    def upload_preset(self, preset_data: dict, auth_token: str | None = None) -> str:
        """Try each backend until the upload succeeds."""
        for backend in self.backends:
            try:
                return backend.upload_preset(preset_data, auth_token)
            except Exception:
                continue
        raise RuntimeError("Upload failed on all backends.")


class GitHubGistBackend(MarketBackend):
    """Market backend using GitHub Gists for preset storage.

    Each gist represents one preset.  Preset metadata is stored in the gist
    description (as a JSON string) and the full preset data lives in a
    ``.json`` file inside the gist.
    """

    def __init__(
        self,
        username: str | None = None,
        gist_ids: list[str] | None = None,
    ) -> None:
        """Initialize the Gist backend.

        Args:
            username: GitHub username whose public gists are listed.
            gist_ids: Explicit list of gist IDs to include.
        """
        self.username = username
        self.gist_ids = gist_ids or []
        self._headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "BitmapVectorStudio/1.0",
        }

    def _fetch_gist(self, gist_id: str) -> dict:
        """Fetch a single gist by ID via the GitHub API."""
        url = f"https://api.github.com/gists/{gist_id}"
        return _http_json(url, headers=self._headers)

    def _parse_preset_from_gist(self, gist: dict) -> dict | None:
        """Extract a preset dict from a GitHub gist response.

        The description is parsed as JSON metadata.  If a ``.json`` file exists
        in the gist, its content is fetched and merged on top of the metadata.
        """
        description = gist.get("description", "")
        files = gist.get("files", {})

        # Try description as metadata first.
        metadata: dict[str, Any] = {}
        try:
            metadata = json.loads(description)
        except json.JSONDecodeError:
            pass

        # Look for a JSON file with the actual preset payload.
        preset_file = None
        for filename, file_info in files.items():
            if filename.endswith(".json"):
                preset_file = file_info
                break

        if preset_file is None:
            # No JSON file – if description was valid JSON, treat it as the preset.
            if metadata:
                metadata.setdefault("id", gist.get("id", ""))
                return metadata
            return None

        raw_url = preset_file.get("raw_url")
        if not raw_url:
            return None

        try:
            content = _http_json(raw_url, headers=self._headers)
        except Exception:
            content = None

        if not isinstance(content, dict):
            # Fall back to metadata-only if the file is unreadable.
            if metadata:
                metadata.setdefault("id", gist.get("id", ""))
                return metadata
            return None

        # Merge file content over metadata so the file is authoritative.
        merged = {**metadata, **content}
        merged.setdefault("id", gist.get("id", ""))
        merged.setdefault("name", Path(preset_file.get("filename", "unknown")).stem)
        merged.setdefault("display_name", merged["name"].replace("_", " ").title())
        return merged

    def list_presets(self) -> list[dict]:
        """List presets from GitHub gists."""
        gists: list[dict] = []

        if self.username:
            url = f"https://api.github.com/users/{self.username}/gists"
            try:
                data = _http_json(url, headers=self._headers)
                if isinstance(data, list):
                    gists.extend(data)
            except Exception as exc:
                logger.warning("Failed to list gists for user %s: %s", self.username, exc)

        for gist_id in self.gist_ids:
            try:
                gist = self._fetch_gist(gist_id)
                gists.append(gist)
            except Exception as exc:
                logger.warning("Failed to fetch gist %s: %s", gist_id, exc)

        presets: list[dict] = []
        for gist in gists:
            preset = self._parse_preset_from_gist(gist)
            if preset:
                presets.append(preset)
        return presets

    def search_presets(self, query: str) -> list[dict]:
        """Search presets by filtering the gist list locally."""
        query_lower = query.lower()
        presets = self.list_presets()
        return [
            p
            for p in presets
            if query_lower in p.get("name", "").lower()
            or query_lower in p.get("display_name", "").lower()
            or any(query_lower in tag.lower() for tag in p.get("tags", []))
        ]

    def download_preset(self, preset_id: str) -> dict:
        """Download a preset from a gist."""
        try:
            gist = self._fetch_gist(preset_id)
        except Exception as exc:
            raise ValueError(f"Failed to download preset {preset_id}: {exc}") from exc

        preset = self._parse_preset_from_gist(gist)
        if preset is None:
            raise ValueError(f"Preset {preset_id} does not contain valid preset data.")
        return preset

    def upload_preset(self, preset_data: dict, auth_token: str | None = None) -> str:
        """Upload a preset as a new public GitHub gist."""
        if not auth_token:
            raise RuntimeError("GitHub auth token is required to upload presets.")

        headers = dict(self._headers)
        headers["Authorization"] = f"token {auth_token}"

        filename = f"{preset_data.get('name', 'preset')}.json"
        payload = {
            "description": json.dumps(preset_data, ensure_ascii=False),
            "public": True,
            "files": {
                filename: {
                    "content": json.dumps(preset_data, indent=2, ensure_ascii=False)
                }
            },
        }

        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

        try:
            response = _http_json(
                "https://api.github.com/gists",
                headers=headers,
                data=data,
                method="POST",
            )
        except Exception as exc:
            raise RuntimeError(f"Failed to upload preset: {exc}") from exc

        gist_id = response.get("id")
        if not gist_id:
            raise RuntimeError("Upload succeeded but no gist ID was returned.")
        return gist_id


class GitHubRepoBackend(MarketBackend):
    """Market backend using a GitHub repository for preset storage.

    Presets are individual ``.json`` files inside the repository.  The backend
    lists files via the GitHub Contents API and downloads raw file content
    from ``raw.githubusercontent.com``.
    """

    def __init__(
        self,
        owner: str,
        repo: str,
        branch: str = "main",
        path: str = "",
    ) -> None:
        """Initialize the repo backend.

        Args:
            owner: Repository owner.
            repo: Repository name.
            branch: Git branch to read from.
            path: Subdirectory path within the repo (no leading/trailing slash).
        """
        self.owner = owner
        self.repo = repo
        self.branch = branch
        self.path = path.strip("/")
        self._headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "BitmapVectorStudio/1.0",
        }

    def _api_url(self, endpoint: str) -> str:
        """Build a GitHub API URL for this repository."""
        base = f"https://api.github.com/repos/{self.owner}/{self.repo}"
        return f"{base}/{endpoint}"

    def _raw_url(self, file_path: str) -> str:
        """Build a raw.githubusercontent.com URL."""
        return (
            f"https://raw.githubusercontent.com/"
            f"{self.owner}/{self.repo}/{self.branch}/{file_path}"
        )

    def list_presets(self) -> list[dict]:
        """List presets by scanning the repository directory."""
        endpoint = f"contents/{self.path}" if self.path else "contents"
        url = self._api_url(endpoint)
        url += f"?ref={self.branch}"

        try:
            items = _http_json(url, headers=self._headers)
        except Exception as exc:
            logger.warning(
                "Failed to list repo contents for %s/%s: %s",
                self.owner,
                self.repo,
                exc,
            )
            return []

        if not isinstance(items, list):
            return []

        presets: list[dict] = []
        for item in items:
            if item.get("type") != "file" or not item.get("name", "").endswith(".json"):
                continue

            name = item["name"].removesuffix(".json")
            preset = {
                "id": item.get("path", name),
                "name": name,
                "display_name": name.replace("_", " ").title(),
                "description": "",
                "author": self.owner,
                "version": "1.0.0",
                "tags": [],
                "downloads": 0,
                "rating": 0.0,
                "options": {},
                "created_at": "",
            }
            presets.append(preset)

        return presets

    def search_presets(self, query: str) -> list[dict]:
        """Search presets by name locally."""
        query_lower = query.lower()
        presets = self.list_presets()
        return [
            p
            for p in presets
            if query_lower in p.get("name", "").lower()
            or query_lower in p.get("display_name", "").lower()
        ]

    def download_preset(self, preset_id: str) -> dict:
        """Download a preset JSON file from the repository."""
        url = self._raw_url(preset_id)
        try:
            data = _http_json(url, headers=self._headers)
        except Exception as exc:
            raise ValueError(f"Failed to download preset {preset_id}: {exc}") from exc

        if not isinstance(data, dict):
            raise ValueError(f"Preset {preset_id} contains invalid JSON.")

        data.setdefault("id", preset_id)
        data.setdefault("name", Path(preset_id).stem)
        return data

    def upload_preset(self, preset_data: dict, auth_token: str | None = None) -> str:
        """Upload a preset to the repository via the GitHub Contents API."""
        if not auth_token:
            raise RuntimeError("GitHub auth token is required to upload presets to a repository.")

        filename = f"{preset_data.get('name', 'preset')}.json"
        file_path = f"{self.path}/{filename}" if self.path else filename

        headers = dict(self._headers)
        headers["Authorization"] = f"token {auth_token}"

        # Check for existing file to obtain SHA for update.
        sha: str | None = None
        check_url = self._api_url(f"contents/{file_path}")
        try:
            existing = _http_json(check_url, headers=headers)
            sha = existing.get("sha")
        except Exception:
            pass

        content = json.dumps(preset_data, indent=2, ensure_ascii=False)
        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        payload: dict[str, Any] = {
            "message": f"Add preset {preset_data.get('name', 'unknown')}",
            "content": encoded,
            "branch": self.branch,
        }
        if sha:
            payload["sha"] = sha

        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

        put_url = self._api_url(f"contents/{file_path}")
        try:
            response = _http_json(put_url, headers=headers, data=data, method="PUT")
        except Exception as exc:
            raise RuntimeError(f"Failed to upload preset: {exc}") from exc

        content_info = response.get("content", {})
        return content_info.get("path", file_path)


# ---------------------------------------------------------------------------
# High-level market interface
# ---------------------------------------------------------------------------

class PresetMarket:
    """High-level preset market interface.

    Provides discovery, search, install, publish, rating, and popularity
    features on top of a :class:`MarketBackend`.
    """

    def __init__(self, backend: MarketBackend | None = None) -> None:
        """Initialize the market.

        Args:
            backend: The market backend to use.  If ``None``, a default
                backend is created from configuration sources or placeholder
                defaults.
        """
        if backend is None:
            backend = self._default_backend()
        self.backend = backend

    @staticmethod
    def _default_backend() -> MarketBackend:
        """Create the default market backend from user configuration.

        Reads ``market_sources`` from the raw config file when present.
        Falls back to placeholder official and community sources.
        """
        raw_cfg = _load_raw_config()
        sources = raw_cfg.get("market_sources", [])

        backends: list[MarketBackend] = []

        if sources:
            for source in sources:
                if not isinstance(source, dict):
                    continue
                kind = source.get("kind", "")
                if kind == "gist":
                    backends.append(
                        GitHubGistBackend(
                            username=source.get("username"),
                            gist_ids=source.get("gist_ids"),
                        )
                    )
                elif kind == "repo":
                    backends.append(
                        GitHubRepoBackend(
                            owner=source.get("owner", ""),
                            repo=source.get("repo", ""),
                            branch=source.get("branch", "main"),
                            path=source.get("path", ""),
                        )
                    )
        else:
            # Placeholder defaults
            backends.append(GitHubGistBackend(gist_ids=[OFFICIAL_GIST_ID]))
            backends.append(
                GitHubRepoBackend(
                    owner=COMMUNITY_REPO_OWNER,
                    repo=COMMUNITY_REPO_NAME,
                    branch="main",
                    path=COMMUNITY_REPO_PATH,
                )
            )

        return MultiBackend(backends)

    def discover_presets(self) -> list[dict]:
        """Discover available presets from the market.

        Returns:
            A list of preset dictionaries.  On network failure an empty
            list is returned so the market degrades gracefully.
        """
        try:
            return self.backend.list_presets()
        except Exception as exc:
            logger.warning("Market discovery failed, falling back to empty list: %s", exc)
            return []

    def search(self, query: str) -> list[dict]:
        """Search presets by query.

        Args:
            query: Free-text search string.

        Returns:
            Matching preset dictionaries.  On network failure an empty
            list is returned.
        """
        try:
            return self.backend.search_presets(query)
        except Exception as exc:
            logger.warning("Market search failed, falling back to empty list: %s", exc)
            return []

    def install(self, preset_id: str, name: str | None = None) -> str:
        """Install a market preset locally.

        Args:
            preset_id: The preset ID in the market.
            name: Optional local name override.

        Returns:
            The local preset name that was saved.

        Raises:
            ValueError: If the preset has no options data.
        """
        preset = self.backend.download_preset(preset_id)
        options_dict = preset.get("options", {})
        if not options_dict:
            raise ValueError(f"Preset {preset_id} has no options data.")

        options = pm._trace_options_from_dict(options_dict)
        local_name = name or preset.get("name", preset_id)
        description = preset.get("description", "")
        pm.save_preset(local_name, options, description=description)
        return local_name

    def publish(self, preset_name: str, auth_token: str) -> str:
        """Publish a local preset to the market.

        Args:
            preset_name: The local preset name.
            auth_token: GitHub authentication token.

        Returns:
            The market preset ID returned by the backend.
        """
        options = pm.load_preset(preset_name)
        options_dict = pm._trace_options_to_dict(options)

        preset_data: dict[str, Any] = {
            "id": "",
            "name": preset_name,
            "display_name": preset_name.replace("_", " ").title(),
            "description": "",
            "author": "",
            "version": "1.0.0",
            "tags": [],
            "downloads": 0,
            "rating": 0.0,
            "options": options_dict,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Enrich with user preset metadata when available.
        user_presets = pm.list_user_presets()
        key = pm._normalize_preset_name(preset_name)
        if key in user_presets:
            preset_data["description"] = user_presets[key].get("description", "")

        return self.backend.upload_preset(preset_data, auth_token)

    def rate(self, preset_id: str, rating: int) -> None:
        """Rate a preset locally.

        Args:
            preset_id: The preset ID.
            rating: Rating value (1–5).

        Raises:
            ValueError: If *rating* is outside the 1–5 range.
        """
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5.")

        ratings = _load_ratings()
        ratings[preset_id] = {
            "rating": rating,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        _save_ratings(ratings)

    def get_popular(self, limit: int = 10) -> list[dict]:
        """Get popular presets sorted by rating and downloads.

        Args:
            limit: Maximum number of presets to return.

        Returns:
            A list of preset dictionaries sorted by effective rating
            (local rating takes precedence over market rating) then
            by download count.
        """
        presets = self.discover_presets()
        ratings = _load_ratings()

        def sort_key(p: dict) -> tuple[float, int]:
            rid = p.get("id", "")
            local_rating = ratings.get(rid, {}).get("rating", 0)
            market_rating = p.get("rating", 0.0)
            effective_rating = float(local_rating) if local_rating else float(market_rating)
            downloads = p.get("downloads", 0)
            return (effective_rating, downloads)

        presets.sort(key=sort_key, reverse=True)
        return presets[:limit]


# ---------------------------------------------------------------------------
# Config helper
# ---------------------------------------------------------------------------

def _load_raw_config() -> dict[str, Any]:
    """Load the raw configuration dict including unknown keys.

    This allows ``market_sources`` (and other future keys) to be read
    without modifying the :class:`Config` dataclass.
    """
    path = _default_config_path()
    if not path.exists():
        return {}
    try:
        if path.suffix in {".yaml", ".yml"} and _has_yaml():
            return _load_yaml(path)
        return _load_json(path)
    except Exception:
        return {}
