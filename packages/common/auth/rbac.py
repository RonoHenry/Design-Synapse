"""Role-Based Access Control (RBAC) system."""

import re
from typing import Dict, List, Optional

from .models import AuthResult, PermissionRule, UserContext


class RoleBasedAccessControl:
    """Role-based access control system for endpoint authorization."""

    def __init__(self):
        """Initialize RBAC system."""
        self.permission_rules: List[PermissionRule] = []
        self.role_permissions: Dict[str, List[str]] = {}
        self._setup_default_permissions()

    def _setup_default_permissions(self):
        """Setup default role permissions mapping."""
        self.role_permissions = {
            "admin": [
                "read:all",
                "write:all",
                "delete:all",
                "manage:users",
                "manage:projects",
                "manage:designs",
                "manage:knowledge",
            ],
            "project_manager": [
                "read:projects",
                "write:projects",
                "read:designs",
                "write:designs",
                "read:knowledge",
                "manage:project_members",
            ],
            "designer": [
                "read:projects",
                "read:designs",
                "write:designs",
                "read:knowledge",
                "write:knowledge",
            ],
            "viewer": ["read:projects", "read:designs", "read:knowledge"],
            "service": ["service:internal", "read:all", "write:all"],
        }

    def add_permission_rule(self, rule: PermissionRule):
        """Add a permission rule for endpoint access.

        Args:
            rule: Permission rule to add
        """
        self.permission_rules.append(rule)

    def add_role_permissions(self, role: str, permissions: List[str]):
        """Add permissions for a role.

        Args:
            role: Role name
            permissions: List of permissions to grant
        """
        if role not in self.role_permissions:
            self.role_permissions[role] = []
        self.role_permissions[role].extend(permissions)

    def get_user_permissions(self, user_context: UserContext) -> List[str]:
        """Get all permissions for a user based on their roles.

        Args:
            user_context: User context with roles

        Returns:
            List of permissions
        """
        permissions = set(user_context.permissions)  # Start with explicit permissions

        # Add permissions from roles
        for role in user_context.roles:
            role_perms = self.role_permissions.get(role, [])
            permissions.update(role_perms)

        return list(permissions)

    def check_permissions(self, user_context: UserContext, endpoint: str) -> AuthResult:
        """Check if user has permissions to access endpoint.

        Args:
            user_context: User context with roles and permissions
            endpoint: Endpoint pattern to check

        Returns:
            AuthResult indicating if access is allowed
        """
        # Find matching permission rule
        matching_rule = self._find_matching_rule(endpoint)

        if not matching_rule:
            # No specific rule found, allow if user has any valid role
            if user_context.roles:
                return AuthResult(success=True, user_context=user_context)
            else:
                return AuthResult(
                    success=False,
                    error_message="No valid roles found",
                    error_code="AUTH_002",
                )

        # Check if service authentication is allowed and user is a service
        if matching_rule.allow_service_auth and user_context.service_name:
            if "service" in user_context.roles:
                return AuthResult(success=True, user_context=user_context)

        # Check role requirements
        if matching_rule.required_roles:
            has_required_role = any(
                role in user_context.roles for role in matching_rule.required_roles
            )
            if not has_required_role:
                return AuthResult(
                    success=False,
                    error_message=f"Required roles: {matching_rule.required_roles}",
                    error_code="AUTH_002",
                )

        # Check permission requirements
        if matching_rule.required_permissions:
            user_permissions = self.get_user_permissions(user_context)
            has_required_permission = any(
                perm in user_permissions for perm in matching_rule.required_permissions
            )
            if not has_required_permission:
                return AuthResult(
                    success=False,
                    error_message=f"Required permissions: {matching_rule.required_permissions}",
                    error_code="AUTH_002",
                )

        return AuthResult(success=True, user_context=user_context)

    def _find_matching_rule(self, endpoint: str) -> Optional[PermissionRule]:
        """Find permission rule matching the endpoint.

        Args:
            endpoint: Endpoint to match

        Returns:
            Matching PermissionRule or None
        """
        for rule in self.permission_rules:
            if self._endpoint_matches_pattern(endpoint, rule.endpoint_pattern):
                return rule
        return None

    def _endpoint_matches_pattern(self, endpoint: str, pattern: str) -> bool:
        """Check if endpoint matches pattern.

        Args:
            endpoint: Endpoint path
            pattern: Pattern to match against

        Returns:
            True if endpoint matches pattern
        """
        # Convert pattern to regex
        # Replace {id} with \d+ and {slug} with [^/]+
        regex_pattern = pattern
        regex_pattern = re.sub(r"\{id\}", r"\\d+", regex_pattern)
        regex_pattern = re.sub(r"\{[^}]+\}", r"[^/]+", regex_pattern)
        regex_pattern = f"^{regex_pattern}$"

        return bool(re.match(regex_pattern, endpoint))

    def setup_default_rules(self):
        """Setup default permission rules for common endpoints."""
        default_rules = [
            # Admin endpoints
            PermissionRule(
                endpoint_pattern="/api/v1/admin/.*",
                required_roles=["admin"],
                required_permissions=[],
                allow_service_auth=True,
                description="Admin endpoints require admin role",
            ),
            # User management
            PermissionRule(
                endpoint_pattern="/api/v1/users/.*",
                required_roles=["admin", "project_manager"],
                required_permissions=["manage:users"],
                allow_service_auth=True,
                description="User management endpoints",
            ),
            # Project endpoints
            PermissionRule(
                endpoint_pattern="/api/v1/projects",
                required_roles=["admin", "project_manager", "designer", "viewer"],
                required_permissions=["read:projects"],
                allow_service_auth=True,
                description="Project read access",
            ),
            PermissionRule(
                endpoint_pattern="/api/v1/projects/{id}",
                required_roles=["admin", "project_manager", "designer"],
                required_permissions=["write:projects"],
                allow_service_auth=True,
                description="Project write access",
            ),
            # Design endpoints
            PermissionRule(
                endpoint_pattern="/api/v1/designs",
                required_roles=["admin", "project_manager", "designer", "viewer"],
                required_permissions=["read:designs"],
                allow_service_auth=True,
                description="Design read access",
            ),
            PermissionRule(
                endpoint_pattern="/api/v1/designs/{id}",
                required_roles=["admin", "project_manager", "designer"],
                required_permissions=["write:designs"],
                allow_service_auth=True,
                description="Design write access",
            ),
            # Knowledge endpoints
            PermissionRule(
                endpoint_pattern="/api/v1/knowledge/.*",
                required_roles=["admin", "project_manager", "designer", "viewer"],
                required_permissions=["read:knowledge"],
                allow_service_auth=True,
                description="Knowledge base access",
            ),
            # Health check endpoints (public)
            PermissionRule(
                endpoint_pattern="/health",
                required_roles=[],
                required_permissions=[],
                allow_service_auth=True,
                description="Health check endpoints are public",
            ),
            PermissionRule(
                endpoint_pattern="/api/v1/health",
                required_roles=[],
                required_permissions=[],
                allow_service_auth=True,
                description="API health check endpoints are public",
            ),
        ]

        for rule in default_rules:
            self.add_permission_rule(rule)
