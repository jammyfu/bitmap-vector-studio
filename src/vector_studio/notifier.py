"""Bitmap Vector Studio 通知系统.

支持 Webhook、Slack、Discord、邮件通知.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class NotifyChannel(Enum):
    WEBHOOK = "webhook"
    SLACK = "slack"
    DISCORD = "discord"
    EMAIL = "email"


@dataclass
class NotifyConfig:
    channel: NotifyChannel
    url: str | None = None
    token: str | None = None
    enabled: bool = True
    events: list[str] | None = None  # 订阅的事件类型


class Notifier:
    """通知器."""

    EVENTS = [
        "convert.start",
        "convert.complete",
        "convert.error",
        "batch.complete",
        "queue.empty",
    ]

    def __init__(self, config_dir: Path | None = None) -> None:
        self.config_dir = config_dir or Path.home() / ".bitmap_vector_studio" / "notifications"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "config.json"
        self._configs: list[NotifyConfig] = []
        self._load_configs()

    def _load_configs(self) -> None:
        if self.config_file.exists():
            try:
                data = json.loads(self.config_file.read_text(encoding="utf-8"))
                self._configs = [
                    NotifyConfig(
                        channel=NotifyChannel(item["channel"]),
                        url=item.get("url"),
                        token=item.get("token"),
                        enabled=item.get("enabled", True),
                        events=item.get("events"),
                    )
                    for item in data
                ]
            except Exception:  # noqa: BLE001
                self._configs = []

    def _save_configs(self) -> None:
        self.config_file.write_text(
            json.dumps(
                [
                    {
                        "channel": c.channel.value,
                        "url": c.url,
                        "token": c.token,
                        "enabled": c.enabled,
                        "events": c.events,
                    }
                    for c in self._configs
                ],
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def add_webhook(self, url: str, events: list[str] | None = None) -> None:
        """添加 Webhook 通知."""
        self._configs.append(
            NotifyConfig(
                channel=NotifyChannel.WEBHOOK,
                url=url,
                events=events or self.EVENTS,
            )
        )
        self._save_configs()

    def add_slack(self, webhook_url: str, events: list[str] | None = None) -> None:
        """添加 Slack 通知."""
        self._configs.append(
            NotifyConfig(
                channel=NotifyChannel.SLACK,
                url=webhook_url,
                events=events or self.EVENTS,
            )
        )
        self._save_configs()

    def add_discord(self, webhook_url: str, events: list[str] | None = None) -> None:
        """添加 Discord 通知."""
        self._configs.append(
            NotifyConfig(
                channel=NotifyChannel.DISCORD,
                url=webhook_url,
                events=events or self.EVENTS,
            )
        )
        self._save_configs()

    def remove(self, index: int) -> bool:
        """移除通知配置."""
        if 0 <= index < len(self._configs):
            self._configs.pop(index)
            self._save_configs()
            return True
        return False

    def list(self) -> list[NotifyConfig]:
        """列出所有通知配置."""
        return self._configs.copy()

    def notify(self, event: str, payload: dict[str, Any]) -> list[tuple[str, bool, str]]:
        """发送通知.

        Returns:
            列表 of (channel, success, message)
        """
        results: list[tuple[str, bool, str]] = []
        for config in self._configs:
            if not config.enabled:
                continue
            if config.events and event not in config.events:
                continue

            try:
                if config.channel == NotifyChannel.WEBHOOK:
                    success = self._send_webhook(config.url, payload)
                elif config.channel == NotifyChannel.SLACK:
                    success = self._send_slack(config.url, event, payload)
                elif config.channel == NotifyChannel.DISCORD:
                    success = self._send_discord(config.url, event, payload)
                else:
                    success = False
                results.append((config.channel.value, success, "ok" if success else "failed"))
            except Exception as e:
                results.append((config.channel.value, False, str(e)))

        return results

    def _send_webhook(self, url: str | None, payload: dict[str, Any]) -> bool:
        """发送通用 Webhook."""
        if not url:
            return False
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200

    def _send_slack(self, url: str | None, event: str, payload: dict[str, Any]) -> bool:
        """发送 Slack 消息."""
        if not url:
            return False
        message = {
            "text": f"Bitmap Vector Studio: {event}",
            "attachments": [
                {
                    "color": "good" if "error" not in event else "danger",
                    "fields": [
                        {"title": k, "value": str(v), "short": True}
                        for k, v in payload.items()
                    ],
                }
            ],
        }
        return self._send_webhook(url, message)

    def _send_discord(self, url: str | None, event: str, payload: dict[str, Any]) -> bool:
        """发送 Discord 消息."""
        if not url:
            return False
        message = {
            "content": f"**Bitmap Vector Studio**: {event}",
            "embeds": [
                {
                    "color": 0x00FF00 if "error" not in event else 0xFF0000,
                    "fields": [
                        {"name": k, "value": str(v)[:1000], "inline": True}
                        for k, v in payload.items()
                    ],
                }
            ],
        }
        return self._send_webhook(url, message)
