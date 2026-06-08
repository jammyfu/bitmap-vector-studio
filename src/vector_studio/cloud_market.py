from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Local auth / config helpers
# ---------------------------------------------------------------------------


def _cloud_config_dir() -> Path:
    """Return the directory used for cloud auth and configuration."""
    directory = Path.home() / ".bitmap_vector_studio" / "cloud"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def save_auth(token: str, backend_url: str | None = None, user_id: str | None = None) -> None:
    """Persist authentication credentials to disk.

    Args:
        token: Authentication bearer token.
        backend_url: Optional custom backend URL.
        user_id: Optional cached user identifier.
    """
    path = _cloud_config_dir() / "auth.json"
    data: dict[str, Any] = {"token": token}
    if backend_url is not None:
        data["backend_url"] = backend_url
    if user_id is not None:
        data["user_id"] = user_id
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    tmp.replace(path)


def load_auth() -> dict[str, str | None]:
    """Load persisted authentication credentials.

    Returns:
        Dictionary with ``token``, ``backend_url`` and ``user_id`` keys.
        Missing or unreadable files yield ``None`` values.
    """
    path = _cloud_config_dir() / "auth.json"
    if not path.exists():
        return {"token": None, "backend_url": None, "user_id": None}
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return {
            "token": data.get("token"),
            "backend_url": data.get("backend_url"),
            "user_id": data.get("user_id"),
        }
    except (json.JSONDecodeError, OSError):
        return {"token": None, "backend_url": None, "user_id": None}


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------


def _http_json_request(
    url: str,
    method: str = "GET",
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Perform an HTTP request and return parsed JSON.

    Args:
        url: Target URL.
        method: HTTP method (defaults to GET).
        data: Optional JSON-serializable request body.
        headers: Optional extra request headers.
        timeout: Socket timeout in seconds.

    Returns:
        Parsed JSON response as a dictionary.

    Raises:
        urllib.error.HTTPError: On HTTP error responses.
        urllib.error.URLError: On network-level failures.
        json.JSONDecodeError: When the response is not valid JSON.
    """
    req_headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if headers:
        req_headers.update(headers)
    body = json.dumps(data, ensure_ascii=False).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class UserAccount:
    """Cloud user account representation."""

    user_id: str
    username: str
    email: str
    tier: str
    credits: int
    created_at: str


# ---------------------------------------------------------------------------
# CloudMarket
# ---------------------------------------------------------------------------


class CloudMarket:
    """Client for the cloud paid market (plugins, presets, and user library)."""

    def __init__(self, backend_url: str = "https://api.bitmap-vector-studio.example") -> None:
        """Initialize the cloud market client.

        Args:
            backend_url: Base URL of the cloud market API.
        """
        self.backend_url = backend_url.rstrip("/")
        self._token: str | None = None

    def set_token(self, token: str) -> None:
        """Set the bearer token for authenticated requests.

        Args:
            token: Bearer token string.
        """
        self._token = token

    def _request(
        self,
        endpoint: str,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute an authenticated request against the backend.

        Args:
            endpoint: API endpoint path (e.g. ``/market/plugins``).
            method: HTTP method.
            data: Optional JSON body.

        Returns:
            Parsed JSON response.

        Raises:
            urllib.error.HTTPError: On HTTP error responses.
            urllib.error.URLError: On network-level failures.
        """
        url = f"{self.backend_url}{endpoint}"
        headers: dict[str, str] = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return _http_json_request(url, method=method, data=data, headers=headers)

    def get_current_user(self) -> dict[str, Any]:
        """Fetch the currently authenticated user profile.

        Returns:
            User dictionary. On failure an empty dict is returned.
        """
        try:
            return self._request("/me")
        except Exception as exc:
            logger.warning("Failed to get current user: %s", exc)
            return {}

    def list_paid_plugins(self) -> list[dict]:
        """List paid plugins available in the market.

        Returns:
            A list of plugin dictionaries. On failure an empty list is
            returned so the CLI degrades gracefully.
        """
        try:
            resp = self._request("/market/plugins")
            return resp.get("plugins", []) if isinstance(resp, dict) else []
        except Exception as exc:
            logger.warning("Failed to list paid plugins: %s", exc)
            return []

    def list_paid_presets(self) -> list[dict]:
        """List paid presets available in the market.

        Returns:
            A list of preset dictionaries. On failure an empty list is
            returned.
        """
        try:
            resp = self._request("/market/presets")
            return resp.get("presets", []) if isinstance(resp, dict) else []
        except Exception as exc:
            logger.warning("Failed to list paid presets: %s", exc)
            return []

    def purchase_item(self, user_id: str, item_id: str) -> dict:
        """Purchase an item from the market.

        Args:
            user_id: Identifier of the purchasing user.
            item_id: Identifier of the item to buy.

        Returns:
            Purchase result dictionary. On failure the dict contains
            ``success: False`` and an ``error`` key.
        """
        try:
            return self._request(
                "/market/purchase",
                method="POST",
                data={"user_id": user_id, "item_id": item_id},
            )
        except Exception as exc:
            logger.warning("Purchase failed: %s", exc)
            return {"success": False, "error": str(exc)}

    def get_user_library(self, user_id: str) -> list[dict]:
        """Retrieve the user's purchased library.

        Args:
            user_id: User identifier.

        Returns:
            A list of purchased item dictionaries. On failure an empty
            list is returned.
        """
        try:
            resp = self._request(f"/users/{user_id}/library")
            return resp.get("items", []) if isinstance(resp, dict) else []
        except Exception as exc:
            logger.warning("Failed to get user library: %s", exc)
            return []

    def publish_item(self, user_id: str, item_type: str, item_data: dict) -> str:
        """Publish a new item to the market.

        Args:
            user_id: Publisher user identifier.
            item_type: Item category (e.g. ``plugin``, ``preset``).
            item_data: Payload describing the item.

        Returns:
            The published item ID. On failure an empty string is returned.
        """
        try:
            resp = self._request(
                "/market/publish",
                method="POST",
                data={"user_id": user_id, "item_type": item_type, "item_data": item_data},
            )
            return resp.get("item_id", "") if isinstance(resp, dict) else ""
        except Exception as exc:
            logger.warning("Publish failed: %s", exc)
            return ""

    def rate_item(self, user_id: str, item_id: str, rating: int) -> bool:
        """Rate a market item.

        Args:
            user_id: User identifier.
            item_id: Item identifier.
            rating: Rating value (1–5).

        Returns:
            ``True`` when the rating was accepted.

        Raises:
            ValueError: If *rating* is outside the 1–5 range.
        """
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5.")
        try:
            resp = self._request(
                "/market/rate",
                method="POST",
                data={"user_id": user_id, "item_id": item_id, "rating": rating},
            )
            return resp.get("success", False) if isinstance(resp, dict) else False
        except Exception as exc:
            logger.warning("Rate failed: %s", exc)
            return False


# ---------------------------------------------------------------------------
# CreditSystem
# ---------------------------------------------------------------------------


class CreditSystem:
    """Client for the cloud credit / virtual currency system."""

    def __init__(self, backend_url: str = "https://api.bitmap-vector-studio.example") -> None:
        """Initialize the credit system client.

        Args:
            backend_url: Base URL of the cloud API.
        """
        self.backend_url = backend_url.rstrip("/")
        self._token: str | None = None

    def set_token(self, token: str) -> None:
        """Set the bearer token for authenticated requests.

        Args:
            token: Bearer token string.
        """
        self._token = token

    def _request(
        self,
        endpoint: str,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute an authenticated request against the backend.

        Args:
            endpoint: API endpoint path.
            method: HTTP method.
            data: Optional JSON body.

        Returns:
            Parsed JSON response.
        """
        url = f"{self.backend_url}{endpoint}"
        headers: dict[str, str] = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return _http_json_request(url, method=method, data=data, headers=headers)

    def add_credits(self, user_id: str, amount: int) -> int:
        """Add credits to a user account.

        Args:
            user_id: Target user identifier.
            amount: Number of credits to add.

        Returns:
            The new balance. On failure ``0`` is returned.
        """
        try:
            resp = self._request(
                f"/users/{user_id}/credits/add",
                method="POST",
                data={"amount": amount},
            )
            return resp.get("balance", 0) if isinstance(resp, dict) else 0
        except Exception as exc:
            logger.warning("Failed to add credits: %s", exc)
            return 0

    def deduct_credits(self, user_id: str, amount: int) -> int:
        """Deduct credits from a user account.

        Args:
            user_id: Target user identifier.
            amount: Number of credits to deduct.

        Returns:
            The new balance. On failure ``0`` is returned.
        """
        try:
            resp = self._request(
                f"/users/{user_id}/credits/deduct",
                method="POST",
                data={"amount": amount},
            )
            return resp.get("balance", 0) if isinstance(resp, dict) else 0
        except Exception as exc:
            logger.warning("Failed to deduct credits: %s", exc)
            return 0

    def get_balance(self, user_id: str) -> int:
        """Query the current credit balance.

        Args:
            user_id: User identifier.

        Returns:
            Current balance. On failure ``0`` is returned.
        """
        try:
            resp = self._request(f"/users/{user_id}/credits")
            return resp.get("balance", 0) if isinstance(resp, dict) else 0
        except Exception as exc:
            logger.warning("Failed to get balance: %s", exc)
            return 0

    def get_transaction_history(self, user_id: str) -> list[dict]:
        """Retrieve the credit transaction history.

        Args:
            user_id: User identifier.

        Returns:
            A list of transaction dictionaries. On failure an empty list
            is returned.
        """
        try:
            resp = self._request(f"/users/{user_id}/credits/history")
            return resp.get("transactions", []) if isinstance(resp, dict) else []
        except Exception as exc:
            logger.warning("Failed to get transaction history: %s", exc)
            return []


# ---------------------------------------------------------------------------
# DeveloperDashboard
# ---------------------------------------------------------------------------


class DeveloperDashboard:
    """Client for the developer revenue and sales dashboard."""

    def __init__(self, backend_url: str = "https://api.bitmap-vector-studio.example") -> None:
        """Initialize the developer dashboard client.

        Args:
            backend_url: Base URL of the cloud API.
        """
        self.backend_url = backend_url.rstrip("/")
        self._token: str | None = None

    def set_token(self, token: str) -> None:
        """Set the bearer token for authenticated requests.

        Args:
            token: Bearer token string.
        """
        self._token = token

    def _request(
        self,
        endpoint: str,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute an authenticated request against the backend.

        Args:
            endpoint: API endpoint path.
            method: HTTP method.
            data: Optional JSON body.

        Returns:
            Parsed JSON response.
        """
        url = f"{self.backend_url}{endpoint}"
        headers: dict[str, str] = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return _http_json_request(url, method=method, data=data, headers=headers)

    def get_sales_report(self, developer_id: str) -> dict:
        """Fetch the sales report for a developer.

        Args:
            developer_id: Developer identifier.

        Returns:
            Sales report dictionary. On failure an empty dict is returned.
        """
        try:
            return self._request(f"/developers/{developer_id}/sales")
        except Exception as exc:
            logger.warning("Failed to get sales report: %s", exc)
            return {}

    def get_revenue(self, developer_id: str) -> float:
        """Fetch the total revenue for a developer.

        Args:
            developer_id: Developer identifier.

        Returns:
            Revenue amount. On failure ``0.0`` is returned.
        """
        try:
            resp = self._request(f"/developers/{developer_id}/revenue")
            return resp.get("revenue", 0.0) if isinstance(resp, dict) else 0.0
        except Exception as exc:
            logger.warning("Failed to get revenue: %s", exc)
            return 0.0

    def withdraw(self, developer_id: str, amount: float) -> bool:
        """Request a withdrawal.

        Args:
            developer_id: Developer identifier.
            amount: Amount to withdraw.

        Returns:
            ``True`` if the withdrawal was accepted. On failure ``False``
            is returned.
        """
        try:
            resp = self._request(
                f"/developers/{developer_id}/withdraw",
                method="POST",
                data={"amount": amount},
            )
            return resp.get("success", False) if isinstance(resp, dict) else False
        except Exception as exc:
            logger.warning("Withdraw failed: %s", exc)
            return False
