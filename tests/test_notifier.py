from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vector_studio.notifier import Notifier, NotifyChannel, NotifyConfig


class TestNotifierConfig:
    def test_add_webhook(self, tmp_path: Path):
        notifier = Notifier(config_dir=tmp_path / "notifications")
        notifier.add_webhook("https://example.com/hook")
        configs = notifier.list()
        assert len(configs) == 1
        assert configs[0].channel == NotifyChannel.WEBHOOK
        assert configs[0].url == "https://example.com/hook"
        assert configs[0].enabled is True

    def test_add_slack(self, tmp_path: Path):
        notifier = Notifier(config_dir=tmp_path / "notifications")
        notifier.add_slack("https://hooks.slack.com/test")
        configs = notifier.list()
        assert len(configs) == 1
        assert configs[0].channel == NotifyChannel.SLACK

    def test_add_discord(self, tmp_path: Path):
        notifier = Notifier(config_dir=tmp_path / "notifications")
        notifier.add_discord("https://discord.com/api/webhooks/test")
        configs = notifier.list()
        assert len(configs) == 1
        assert configs[0].channel == NotifyChannel.DISCORD

    def test_remove(self, tmp_path: Path):
        notifier = Notifier(config_dir=tmp_path / "notifications")
        notifier.add_webhook("https://example.com/hook")
        assert notifier.remove(0) is True
        assert notifier.list() == []
        assert notifier.remove(0) is False

    def test_custom_events(self, tmp_path: Path):
        notifier = Notifier(config_dir=tmp_path / "notifications")
        notifier.add_webhook("https://example.com/hook", events=["convert.complete"])
        configs = notifier.list()
        assert configs[0].events == ["convert.complete"]

    def test_persistence(self, tmp_path: Path):
        config_dir = tmp_path / "notifications"
        notifier = Notifier(config_dir=config_dir)
        notifier.add_webhook("https://example.com/hook", events=["convert.complete"])
        notifier.add_slack("https://hooks.slack.com/test")

        # Create a new instance pointing at the same directory
        notifier2 = Notifier(config_dir=config_dir)
        configs = notifier2.list()
        assert len(configs) == 2
        assert configs[0].channel == NotifyChannel.WEBHOOK
        assert configs[1].channel == NotifyChannel.SLACK


class TestNotifierSend:
    def test_notify_webhook_success(self, tmp_path: Path):
        notifier = Notifier(config_dir=tmp_path / "notifications")
        notifier.add_webhook("https://example.com/hook")

        with patch("vector_studio.notifier.urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_resp)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
            results = notifier.notify("convert.complete", {"file": "test.png"})

        assert len(results) == 1
        assert results[0][0] == "webhook"
        assert results[0][1] is True

    def test_notify_skips_disabled(self, tmp_path: Path):
        notifier = Notifier(config_dir=tmp_path / "notifications")
        notifier.add_webhook("https://example.com/hook")
        notifier._configs[0].enabled = False
        results = notifier.notify("convert.complete", {"file": "test.png"})
        assert results == []

    def test_notify_filters_by_event(self, tmp_path: Path):
        notifier = Notifier(config_dir=tmp_path / "notifications")
        notifier.add_webhook("https://example.com/hook", events=["convert.complete"])

        with patch("vector_studio.notifier.urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_resp)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
            results = notifier.notify("convert.error", {"file": "test.png"})

        assert results == []

    def test_notify_slack_format(self, tmp_path: Path):
        notifier = Notifier(config_dir=tmp_path / "notifications")
        notifier.add_slack("https://hooks.slack.com/test")

        with patch("vector_studio.notifier.urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_resp)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
            results = notifier.notify("convert.complete", {"file": "test.png"})

        assert len(results) == 1
        assert results[0][0] == "slack"
        # Verify Slack payload format
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        payload = json.loads(req.data)
        assert "attachments" in payload
        assert payload["attachments"][0]["color"] == "good"

    def test_notify_discord_format(self, tmp_path: Path):
        notifier = Notifier(config_dir=tmp_path / "notifications")
        notifier.add_discord("https://discord.com/api/webhooks/test")

        with patch("vector_studio.notifier.urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_resp)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
            results = notifier.notify("convert.error", {"file": "test.png"})

        assert len(results) == 1
        assert results[0][0] == "discord"
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        payload = json.loads(req.data)
        assert "embeds" in payload
        assert payload["embeds"][0]["color"] == 0xFF0000

    def test_notify_error_event_color(self, tmp_path: Path):
        notifier = Notifier(config_dir=tmp_path / "notifications")
        notifier.add_slack("https://hooks.slack.com/test")

        with patch("vector_studio.notifier.urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_resp)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
            results = notifier.notify("convert.error", {"file": "test.png"})

        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        payload = json.loads(req.data)
        assert payload["attachments"][0]["color"] == "danger"
