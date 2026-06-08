from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Role permissions
# ---------------------------------------------------------------------------

ALL_PERMISSIONS = [
    "convert",
    "edit",
    "upload",
    "download",
    "view",
    "admin",
    "publish",
    "rate",
    "delete",
    "manage_members",
    "manage_settings",
]


class RolePermissions:
    """Enterprise role-based permission system with audit logging."""

    ROLES: dict[str, list[str]] = {
        "admin": ALL_PERMISSIONS,
        "editor": ["convert", "edit", "upload", "download", "view", "publish", "rate"],
        "viewer": ["view", "download"],
        "guest": ["view"],
    }

    def __init__(self) -> None:
        """Initialize the role permission manager."""
        self.audit_log: list[dict[str, Any]] = []
        self._user_roles: dict[str, str] = {}

    def assign_role(self, user_id: str, role: str) -> bool:
        """Assign a role to a user.

        Args:
            user_id: The user identifier.
            role: Role name (must exist in ``ROLES``).

        Returns:
            ``True`` if the role was assigned successfully.
        """
        if role not in self.ROLES:
            logger.warning("Unknown role '%s' for user %s", role, user_id)
            return False
        self._user_roles[user_id] = role
        self.log_action(user_id, "role_assigned", f"role={role}")
        return True

    def check_permission(self, user_id: str, permission: str) -> bool:
        """Check whether a user has a specific permission.

        Args:
            user_id: The user identifier.
            permission: Permission string to check.

        Returns:
            ``True`` if the user has the permission.
        """
        role = self._user_roles.get(user_id, "guest")
        perms = self.ROLES.get(role, [])
        return permission in perms

    def get_user_role(self, user_id: str) -> str:
        """Return the current role for a user.

        Args:
            user_id: The user identifier.

        Returns:
            The role name, defaulting to ``guest``.
        """
        return self._user_roles.get(user_id, "guest")

    def log_action(self, user_id: str, action: str, resource: str) -> None:
        """Record an action in the audit log.

        Args:
            user_id: The user who performed the action.
            action: Action name.
            resource: Target resource or metadata.
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "action": action,
            "resource": resource,
        }
        self.audit_log.append(entry)
        logger.info("Audit: %s by %s on %s", action, user_id, resource)

    def get_audit_log(self, user_id: str | None = None) -> list[dict[str, Any]]:
        """Retrieve audit log entries, optionally filtered by user.

        Args:
            user_id: Optional user filter.

        Returns:
            List of audit log entries.
        """
        if user_id is None:
            return list(self.audit_log)
        return [e for e in self.audit_log if e["user_id"] == user_id]


# ---------------------------------------------------------------------------
# Team workspace
# ---------------------------------------------------------------------------


class TeamWorkspace:
    """Enterprise team workspace with member management."""

    def __init__(
        self,
        workspace_id: str | None = None,
        name: str = "",
        owner: str = "",
        settings: dict[str, Any] | None = None,
    ) -> None:
        """Initialize a team workspace.

        Args:
            workspace_id: Unique workspace identifier. Auto-generated if ``None``.
            name: Human-readable workspace name.
            owner: User ID of the workspace owner.
            settings: Optional workspace settings dictionary.
        """
        self.workspace_id = workspace_id or str(uuid.uuid4())
        self.name = name
        self.owner = owner
        self.members: dict[str, str] = {owner: "admin"} if owner else {}
        self.settings: dict[str, Any] = settings or {}
        self._permissions = RolePermissions()
        for uid, role in self.members.items():
            self._permissions.assign_role(uid, role)

    def add_member(self, user_id: str, role: str) -> bool:
        """Add a member to the workspace.

        Args:
            user_id: The user to add.
            role: Role to assign.

        Returns:
            ``True`` if the member was added.
        """
        if user_id in self.members:
            logger.warning("User %s is already a member of workspace %s", user_id, self.workspace_id)
            return False
        if role not in RolePermissions.ROLES:
            logger.warning("Invalid role '%s'", role)
            return False
        self.members[user_id] = role
        self._permissions.assign_role(user_id, role)
        self._permissions.log_action(user_id, "member_added", f"workspace={self.workspace_id}")
        return True

    def remove_member(self, user_id: str) -> bool:
        """Remove a member from the workspace.

        Args:
            user_id: The user to remove.

        Returns:
            ``True`` if the member was removed.
        """
        if user_id == self.owner:
            logger.warning("Cannot remove owner %s from workspace %s", user_id, self.workspace_id)
            return False
        if user_id not in self.members:
            return False
        del self.members[user_id]
        self._permissions._user_roles.pop(user_id, None)
        self._permissions.log_action(user_id, "member_removed", f"workspace={self.workspace_id}")
        return True

    def set_role(self, user_id: str, role: str) -> bool:
        """Change the role of an existing member.

        Args:
            user_id: The target user.
            role: New role to assign.

        Returns:
            ``True`` if the role was updated.
        """
        if user_id not in self.members:
            return False
        if role not in RolePermissions.ROLES:
            return False
        self.members[user_id] = role
        self._permissions.assign_role(user_id, role)
        self._permissions.log_action(user_id, "role_changed", f"workspace={self.workspace_id},role={role}")
        return True

    def get_member_permissions(self, user_id: str) -> list[str]:
        """Get the permission list for a workspace member.

        Args:
            user_id: The user identifier.

        Returns:
            List of permission strings. Empty if the user is not a member.
        """
        role = self.members.get(user_id)
        if role is None:
            return []
        return list(RolePermissions.ROLES.get(role, []))

    def get_audit_log(self) -> list[dict[str, Any]]:
        """Return the workspace audit log.

        Returns:
            List of audit log entries.
        """
        return self._permissions.get_audit_log()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the workspace to a dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "workspace_id": self.workspace_id,
            "name": self.name,
            "owner": self.owner,
            "members": dict(self.members),
            "settings": dict(self.settings),
            "audit_log": list(self._permissions.audit_log),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TeamWorkspace:
        """Restore a workspace from a dictionary.

        Args:
            data: Serialized workspace data.

        Returns:
            A new ``TeamWorkspace`` instance.
        """
        ws = cls(
            workspace_id=data.get("workspace_id"),
            name=data.get("name", ""),
            owner=data.get("owner", ""),
            settings=data.get("settings", {}),
        )
        ws.members = dict(data.get("members", {}))
        for uid, role in ws.members.items():
            ws._permissions.assign_role(uid, role)
        # Restore audit log if present
        for entry in data.get("audit_log", []):
            ws._permissions.audit_log.append(dict(entry))
        return ws


# ---------------------------------------------------------------------------
# SSO integration
# ---------------------------------------------------------------------------


class SSOIntegration:
    """Single Sign-On integration supporting Google, GitHub, SAML and LDAP."""

    SUPPORTED_PROVIDERS = {"google", "github", "saml", "ldap"}

    def __init__(self) -> None:
        """Initialize the SSO integration manager."""
        self._configs: dict[str, dict[str, Any]] = {}
        self._tokens: dict[str, dict[str, Any]] = {}

    def configure_sso(self, provider: str, config: dict[str, Any]) -> bool:
        """Configure an SSO provider.

        Args:
            provider: Provider name (``google``, ``github``, ``saml``, ``ldap``).
            config: Provider-specific configuration dictionary.

        Returns:
            ``True`` if the provider was configured successfully.
        """
        provider = provider.lower()
        if provider not in self.SUPPORTED_PROVIDERS:
            logger.warning("Unsupported SSO provider: %s", provider)
            return False
        self._configs[provider] = dict(config)
        logger.info("Configured SSO provider: %s", provider)
        return True

    def authenticate(self, token: str) -> dict[str, Any] | None:
        """Validate an SSO token and return user identity.

        Args:
            token: The SSO token string.

        Returns:
            User identity dictionary or ``None`` if invalid.
        """
        # Simulated token validation – in production this would verify
        # JWT signatures or call the IdP introspection endpoint.
        if not token or len(token) < 8:
            return None
        # Simple mock: tokens starting with "mock_" are treated as test tokens.
        if token.startswith("mock_"):
            user_id = token.replace("mock_", "")
            return {
                "user_id": user_id,
                "email": f"{user_id}@example.com",
                "provider": "mock",
                "authenticated": True,
            }
        # For real tokens we would validate against the configured provider.
        # Return a generic success for any non-trivial token in this stub.
        return {
            "user_id": f"user_{token[:8]}",
            "email": f"user_{token[:8]}@example.com",
            "provider": "unknown",
            "authenticated": True,
        }

    def get_user_info(self, token: str) -> dict[str, Any]:
        """Fetch detailed user information from an SSO token.

        Args:
            token: The SSO token string.

        Returns:
            User information dictionary. Returns an empty dict on failure.
        """
        auth = self.authenticate(token)
        if auth is None:
            return {}
        # Enrich with provider-specific data when available.
        provider = auth.get("provider", "unknown")
        info: dict[str, Any] = {
            "user_id": auth.get("user_id", ""),
            "email": auth.get("email", ""),
            "provider": provider,
            "roles": [],
        }
        if provider in self._configs:
            info["sso_configured"] = True
        return info

    def get_configured_providers(self) -> list[str]:
        """List currently configured SSO providers.

        Returns:
            List of provider names.
        """
        return list(self._configs.keys())
