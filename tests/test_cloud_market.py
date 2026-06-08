import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from vector_studio.cloud_market import (
    CloudMarket,
    CreditSystem,
    DeveloperDashboard,
    UserAccount,
    _cloud_config_dir,
    load_auth,
    save_auth,
)
from vector_studio.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_cloud_config(monkeypatch, tmp_path):
    """Redirect cloud auth storage into a temporary directory."""
    from vector_studio import cloud_market as cm

    monkeypatch.setattr(cm, "_cloud_config_dir", lambda: tmp_path)
    auth_file = tmp_path / "auth.json"
    auth_file.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# UserAccount
# ---------------------------------------------------------------------------


class TestUserAccount:
    def test_user_account_fields(self):
        """UserAccount dataclass stores all expected fields."""
        account = UserAccount(
            user_id="u1",
            username="alice",
            email="alice@example.com",
            tier="pro",
            credits=100,
            created_at="2024-01-01T00:00:00+00:00",
        )
        assert account.user_id == "u1"
        assert account.username == "alice"
        assert account.email == "alice@example.com"
        assert account.tier == "pro"
        assert account.credits == 100
        assert account.created_at == "2024-01-01T00:00:00+00:00"


# ---------------------------------------------------------------------------
# CloudMarket
# ---------------------------------------------------------------------------


class TestCloudMarket:
    def test_list_paid_plugins_success(self):
        """list_paid_plugins returns plugins on successful response."""
        market = CloudMarket("https://example.com")
        with patch("vector_studio.cloud_market.urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(
                {"plugins": [{"id": "p1", "name": "Plugin1"}]}
            ).encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_response
            plugins = market.list_paid_plugins()
        assert len(plugins) == 1
        assert plugins[0]["id"] == "p1"

    def test_list_paid_plugins_failure_returns_empty(self):
        """list_paid_plugins gracefully returns an empty list on network failure."""
        market = CloudMarket("https://example.com")
        with patch(
            "vector_studio.cloud_market.urllib.request.urlopen",
            side_effect=Exception("network error"),
        ):
            plugins = market.list_paid_plugins()
        assert plugins == []

    def test_list_paid_presets_success(self):
        """list_paid_presets returns presets on successful response."""
        market = CloudMarket("https://example.com")
        with patch("vector_studio.cloud_market.urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(
                {"presets": [{"id": "pr1", "name": "Preset1"}]}
            ).encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_response
            presets = market.list_paid_presets()
        assert len(presets) == 1
        assert presets[0]["id"] == "pr1"

    def test_purchase_item_success(self):
        """purchase_item returns the server response on success."""
        market = CloudMarket("https://example.com")
        with patch("vector_studio.cloud_market.urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(
                {"success": True, "remaining_credits": 50}
            ).encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_response
            result = market.purchase_item("u1", "item-123")
        assert result["success"] is True
        assert result["remaining_credits"] == 50

    def test_purchase_item_failure_returns_dict(self):
        """purchase_item returns a failure dict on network error."""
        market = CloudMarket("https://example.com")
        with patch(
            "vector_studio.cloud_market.urllib.request.urlopen",
            side_effect=Exception("network error"),
        ):
            result = market.purchase_item("u1", "item-123")
        assert result["success"] is False
        assert "error" in result

    def test_get_user_library(self):
        """get_user_library returns items on successful response."""
        market = CloudMarket("https://example.com")
        with patch("vector_studio.cloud_market.urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(
                {"items": [{"item_id": "i1", "name": "Item1"}]}
            ).encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_response
            items = market.get_user_library("u1")
        assert len(items) == 1
        assert items[0]["item_id"] == "i1"

    def test_publish_item(self):
        """publish_item returns the new item ID on success."""
        market = CloudMarket("https://example.com")
        with patch("vector_studio.cloud_market.urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(
                {"item_id": "new-item-456"}
            ).encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_response
            item_id = market.publish_item("u1", "plugin", {"name": "MyPlugin"})
        assert item_id == "new-item-456"

    def test_rate_item(self):
        """rate_item returns True when the server accepts the rating."""
        market = CloudMarket("https://example.com")
        with patch("vector_studio.cloud_market.urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(
                {"success": True}
            ).encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_response
            assert market.rate_item("u1", "item-1", 5) is True

    def test_rate_item_out_of_range(self):
        """rate_item rejects ratings outside the 1–5 range."""
        market = CloudMarket("https://example.com")
        with pytest.raises(ValueError, match="Rating must be between 1 and 5"):
            market.rate_item("u1", "item-1", 0)
        with pytest.raises(ValueError, match="Rating must be between 1 and 5"):
            market.rate_item("u1", "item-1", 6)

    def test_get_current_user(self):
        """get_current_user returns the user profile on success."""
        market = CloudMarket("https://example.com")
        with patch("vector_studio.cloud_market.urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(
                {"user_id": "u1", "username": "alice"}
            ).encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_response
            user = market.get_current_user()
        assert user["user_id"] == "u1"
        assert user["username"] == "alice"


# ---------------------------------------------------------------------------
# CreditSystem
# ---------------------------------------------------------------------------


class TestCreditSystem:
    def test_add_credits(self):
        """add_credits returns the new balance."""
        cs = CreditSystem("https://example.com")
        with patch("vector_studio.cloud_market.urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(
                {"balance": 150}
            ).encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_response
            balance = cs.add_credits("u1", 50)
        assert balance == 150

    def test_deduct_credits(self):
        """deduct_credits returns the new balance."""
        cs = CreditSystem("https://example.com")
        with patch("vector_studio.cloud_market.urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(
                {"balance": 80}
            ).encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_response
            balance = cs.deduct_credits("u1", 20)
        assert balance == 80

    def test_get_balance(self):
        """get_balance returns the current balance."""
        cs = CreditSystem("https://example.com")
        with patch("vector_studio.cloud_market.urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(
                {"balance": 200}
            ).encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_response
            assert cs.get_balance("u1") == 200

    def test_get_transaction_history(self):
        """get_transaction_history returns a list of transactions."""
        cs = CreditSystem("https://example.com")
        with patch("vector_studio.cloud_market.urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(
                {"transactions": [{"id": "t1", "amount": 10}]}
            ).encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_response
            history = cs.get_transaction_history("u1")
        assert len(history) == 1
        assert history[0]["amount"] == 10


# ---------------------------------------------------------------------------
# DeveloperDashboard
# ---------------------------------------------------------------------------


class TestDeveloperDashboard:
    def test_get_sales_report(self):
        """get_sales_report returns the report dictionary."""
        dash = DeveloperDashboard("https://example.com")
        with patch("vector_studio.cloud_market.urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(
                {"total_sales": 42, "revenue": 123.45}
            ).encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_response
            report = dash.get_sales_report("dev1")
        assert report["total_sales"] == 42

    def test_get_revenue(self):
        """get_revenue returns the revenue float."""
        dash = DeveloperDashboard("https://example.com")
        with patch("vector_studio.cloud_market.urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(
                {"revenue": 999.99}
            ).encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_response
            assert dash.get_revenue("dev1") == 999.99

    def test_withdraw(self):
        """withdraw returns True on success."""
        dash = DeveloperDashboard("https://example.com")
        with patch("vector_studio.cloud_market.urllib.request.urlopen") as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(
                {"success": True}
            ).encode("utf-8")
            mock_urlopen.return_value.__enter__.return_value = mock_response
            assert dash.withdraw("dev1", 100.0) is True


# ---------------------------------------------------------------------------
# Auth storage
# ---------------------------------------------------------------------------


class TestAuthStorage:
    def test_save_and_load_auth(self):
        """save_auth persists token, backend_url and user_id."""
        save_auth("my-token", "https://api.example.com", "user-1")
        auth = load_auth()
        assert auth["token"] == "my-token"
        assert auth["backend_url"] == "https://api.example.com"
        assert auth["user_id"] == "user-1"

    def test_load_auth_missing_file(self):
        """load_auth returns None values when no auth file exists."""
        auth = load_auth()
        assert auth["token"] is None
        assert auth["backend_url"] is None
        assert auth["user_id"] is None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestAccountCLI:
    def test_account_login(self):
        """account login stores the token and prints success."""
        result = runner.invoke(app, ["account", "login", "test-token"])
        assert result.exit_code == 0
        assert "Logged in successfully" in result.output
        auth = load_auth()
        assert auth["token"] == "test-token"

    def test_account_info_not_logged_in(self):
        """account info exits early when no token is stored."""
        result = runner.invoke(app, ["account", "info"])
        assert result.exit_code == 1
        assert "Not logged in" in result.output

    def test_account_info_success(self):
        """account info renders a table with user details."""
        save_auth("tok", "https://example.com", "u1")
        with patch(
            "vector_studio.cloud_market.CloudMarket.get_current_user",
            return_value={
                "user_id": "u1",
                "username": "alice",
                "email": "a@example.com",
                "tier": "pro",
                "credits": 100,
            },
        ):
            result = runner.invoke(app, ["account", "info"])
        assert result.exit_code == 0
        assert "alice" in result.output
        assert "pro" in result.output
        assert "100" in result.output

    def test_account_credits(self):
        """account credits prints the current balance."""
        save_auth("tok", "https://example.com", "u1")
        with patch(
            "vector_studio.cloud_market.CreditSystem.get_balance",
            return_value=250,
        ):
            result = runner.invoke(app, ["account", "credits"])
        assert result.exit_code == 0
        assert "250" in result.output


class TestCloudMarketCLI:
    def test_market_purchase(self):
        """market purchase calls CloudMarket.purchase_item and prints success."""
        save_auth("tok", "https://example.com", "u1")
        with patch(
            "vector_studio.cloud_market.CloudMarket.purchase_item",
            return_value={"success": True, "remaining_credits": 90},
        ):
            result = runner.invoke(app, ["market", "purchase", "item-123"])
        assert result.exit_code == 0
        assert "Purchased" in result.output
        assert "item-123" in result.output

    def test_market_purchase_failure(self):
        """market purchase exits with code 1 on failure."""
        save_auth("tok", "https://example.com", "u1")
        with patch(
            "vector_studio.cloud_market.CloudMarket.purchase_item",
            return_value={"success": False, "error": "Insufficient credits"},
        ):
            result = runner.invoke(app, ["market", "purchase", "item-123"])
        assert result.exit_code == 1
        assert "Insufficient credits" in result.output

    def test_market_library(self):
        """market library renders a table of purchased items."""
        save_auth("tok", "https://example.com", "u1")
        with patch(
            "vector_studio.cloud_market.CloudMarket.get_user_library",
            return_value=[
                {
                    "item_id": "i1",
                    "name": "Plugin A",
                    "item_type": "plugin",
                    "purchased_at": "2024-01-01",
                }
            ],
        ):
            result = runner.invoke(app, ["market", "library"])
        assert result.exit_code == 0
        assert "Plugin A" in result.output

    def test_market_library_empty(self):
        """market library prints a friendly message when empty."""
        save_auth("tok", "https://example.com", "u1")
        with patch(
            "vector_studio.cloud_market.CloudMarket.get_user_library",
            return_value=[],
        ):
            result = runner.invoke(app, ["market", "library"])
        assert result.exit_code == 0
        assert "empty" in result.output.lower() or "Your library is empty" in result.output

    def test_market_publish_item(self, tmp_path):
        """market publish-item uploads a JSON file and prints the item ID."""
        file_path = tmp_path / "item.json"
        file_path.write_text(json.dumps({"version": "1.0"}), encoding="utf-8")
        save_auth("tok", "https://example.com", "u1")
        with patch(
            "vector_studio.cloud_market.CloudMarket.publish_item",
            return_value="new-id",
        ):
            result = runner.invoke(
                app,
                [
                    "market",
                    "publish-item",
                    str(file_path),
                    "--name",
                    "My Item",
                    "--type",
                    "plugin",
                ],
            )
        assert result.exit_code == 0
        assert "new-id" in result.output

    def test_market_publish_item_invalid_json(self, tmp_path):
        """market publish-item exits with code 1 for invalid JSON."""
        file_path = tmp_path / "item.json"
        file_path.write_text("not json", encoding="utf-8")
        save_auth("tok", "https://example.com", "u1")
        result = runner.invoke(
            app,
            [
                "market",
                "publish-item",
                str(file_path),
                "--name",
                "Bad Item",
                "--type",
                "plugin",
            ],
        )
        assert result.exit_code == 1
        assert "Invalid JSON" in result.output

    def test_market_commands_require_login(self):
        """Cloud market commands exit when the user is not logged in."""
        # Ensure no auth file exists
        auth_file = _cloud_config_dir() / "auth.json"
        auth_file.unlink(missing_ok=True)

        result = runner.invoke(app, ["market", "purchase", "item-1"])
        assert result.exit_code == 1
        assert "Not logged in" in result.output

        result = runner.invoke(app, ["market", "library"])
        assert result.exit_code == 1
        assert "Not logged in" in result.output
