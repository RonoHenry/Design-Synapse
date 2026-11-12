"""Tests for role-based access control enforcement."""

import pytest

from ..models import AuthResult, PermissionRule, UserContext
from ..rbac import RoleBasedAccessControl


class TestRoleBasedAccessControl:
    """Test role-based access control system."""

    @pytest.fixture
    def rbac(self):
        """RBAC instance with default setup."""
        rbac = RoleBasedAccessControl()
        rbac.setup_default_rules()
        return rbac

    @pytest.fixture
    def admin_user(self):
        """Admin user context."""
        return UserContext(
            user_id="admin123",
            email="admin@example.com",
            roles=["admin"],
            permissions=["read:all", "write:all", "manage:users"],
        )

    @pytest.fixture
    def designer_user(self):
        """Designer user context."""
        return UserContext(
            user_id="designer123",
            email="designer@example.com",
            roles=["designer"],
            permissions=["read:projects", "write:designs", "read:knowledge"],
        )

    @pytest.fixture
    def viewer_user(self):
        """Viewer user context."""
        return UserContext(
            user_id="viewer123",
            email="viewer@example.com",
            roles=["viewer"],
            permissions=["read:projects", "read:designs"],
        )

    @pytest.fixture
    def service_user(self):
        """Service user context."""
        return UserContext(
            user_id="service:design-service",
            email="design-service@internal.service",
            roles=["service"],
            permissions=["service:internal", "read:all", "write:all"],
            service_name="design-service",
        )

    def test_default_role_permissions_setup(self, rbac):
        """Test default role permissions are properly configured."""
        admin_perms = rbac.role_permissions["admin"]
        assert "read:all" in admin_perms
        assert "write:all" in admin_perms
        assert "manage:users" in admin_perms

        designer_perms = rbac.role_permissions["designer"]
        assert "read:designs" in designer_perms
        assert "write:designs" in designer_perms
        assert "read:knowledge" in designer_perms

        viewer_perms = rbac.role_permissions["viewer"]
        assert "read:projects" in viewer_perms
        assert "read:designs" in viewer_perms
        assert "write:designs" not in viewer_perms

    def test_get_user_permissions_from_roles(self, rbac, designer_user):
        """Test getting user permissions from roles."""
        permissions = rbac.get_user_permissions(designer_user)

        # Should include both explicit permissions and role-based permissions
        assert "read:projects" in permissions
        assert "write:designs" in permissions
        assert "read:knowledge" in permissions

    def test_get_user_permissions_multiple_roles(self, rbac):
        """Test getting permissions for user with multiple roles."""
        multi_role_user = UserContext(
            user_id="multi123",
            email="multi@example.com",
            roles=["designer", "viewer"],
            permissions=["custom:permission"],
        )

        permissions = rbac.get_user_permissions(multi_role_user)

        # Should include permissions from both roles plus explicit permissions
        assert "read:designs" in permissions  # From both roles
        assert "write:designs" in permissions  # From designer role
        assert "custom:permission" in permissions  # Explicit permission

    def test_check_permissions_admin_access(self, rbac, admin_user):
        """Test admin access to admin endpoints."""
        result = rbac.check_permissions(admin_user, "/api/v1/admin/users")

        assert result.success is True
        assert result.user_context == admin_user

    def test_check_permissions_designer_denied_admin(self, rbac, designer_user):
        """Test designer denied access to admin endpoints."""
        result = rbac.check_permissions(designer_user, "/api/v1/admin/users")

        assert result.success is False
        assert result.error_code == "AUTH_002"
        assert "admin" in result.error_message

    def test_check_permissions_service_auth_allowed(self, rbac, service_user):
        """Test service authentication allowed for endpoints."""
        result = rbac.check_permissions(service_user, "/api/v1/projects")

        assert result.success is True
        assert result.user_context == service_user

    def test_check_permissions_viewer_read_access(self, rbac, viewer_user):
        """Test viewer read access to projects."""
        result = rbac.check_permissions(viewer_user, "/api/v1/projects")

        assert result.success is True

    def test_check_permissions_viewer_denied_write(self, rbac, viewer_user):
        """Test viewer denied write access to projects."""
        result = rbac.check_permissions(viewer_user, "/api/v1/projects/123")

        assert result.success is False
        assert result.error_code == "AUTH_002"

    def test_check_permissions_health_endpoint_public(self, rbac, viewer_user):
        """Test health endpoints are accessible to all users."""
        result = rbac.check_permissions(viewer_user, "/health")
        assert result.success is True

        result = rbac.check_permissions(viewer_user, "/api/v1/health")
        assert result.success is True

    def test_check_permissions_no_matching_rule(self, rbac, designer_user):
        """Test access when no specific rule matches."""
        # Custom endpoint not covered by default rules
        result = rbac.check_permissions(designer_user, "/api/v1/custom/endpoint")

        # Should allow access if user has valid roles
        assert result.success is True

    def test_check_permissions_no_roles(self, rbac):
        """Test access denied for user with no roles."""
        no_role_user = UserContext(
            user_id="norole123", email="norole@example.com", roles=[], permissions=[]
        )

        result = rbac.check_permissions(no_role_user, "/api/v1/projects")

        assert result.success is False
        assert result.error_code == "AUTH_002"

    def test_add_permission_rule(self, rbac):
        """Test adding custom permission rule."""
        custom_rule = PermissionRule(
            endpoint_pattern="/api/v1/reports/{id}",
            required_roles=["admin", "analyst"],
            required_permissions=["read:reports"],
            allow_service_auth=True,
            description="Report access",
        )

        rbac.add_permission_rule(custom_rule)

        # Test rule is applied
        analyst_user = UserContext(
            user_id="analyst123",
            email="analyst@example.com",
            roles=["analyst"],
            permissions=["read:reports"],
        )

        result = rbac.check_permissions(analyst_user, "/api/v1/reports/123")
        assert result.success is True

    def test_add_role_permissions(self, rbac):
        """Test adding permissions to a role."""
        rbac.add_role_permissions("designer", ["new:permission", "another:permission"])

        designer_perms = rbac.role_permissions["designer"]
        assert "new:permission" in designer_perms
        assert "another:permission" in designer_perms

    def test_endpoint_pattern_matching(self, rbac):
        """Test endpoint pattern matching with parameters."""
        # Test ID parameter matching
        assert rbac._endpoint_matches_pattern(
            "/api/v1/projects/123", "/api/v1/projects/{id}"
        )
        assert rbac._endpoint_matches_pattern(
            "/api/v1/designs/456", "/api/v1/designs/{id}"
        )

        # Test slug parameter matching
        assert rbac._endpoint_matches_pattern(
            "/api/v1/users/john-doe", "/api/v1/users/{slug}"
        )

        # Test non-matching patterns
        assert not rbac._endpoint_matches_pattern(
            "/api/v1/projects", "/api/v1/projects/{id}"
        )
        assert not rbac._endpoint_matches_pattern(
            "/api/v1/projects/123/comments", "/api/v1/projects/{id}"
        )

    def test_endpoint_pattern_wildcard_matching(self, rbac):
        """Test wildcard pattern matching."""
        # Admin endpoints with wildcard
        assert rbac._endpoint_matches_pattern("/api/v1/admin/users", "/api/v1/admin/.*")
        assert rbac._endpoint_matches_pattern(
            "/api/v1/admin/settings/config", "/api/v1/admin/.*"
        )

        # Knowledge endpoints
        assert rbac._endpoint_matches_pattern(
            "/api/v1/knowledge/search", "/api/v1/knowledge/.*"
        )
        assert rbac._endpoint_matches_pattern(
            "/api/v1/knowledge/resources/123", "/api/v1/knowledge/.*"
        )

    def test_permission_rule_with_service_auth_disabled(self, rbac, service_user):
        """Test permission rule with service auth disabled."""
        no_service_rule = PermissionRule(
            endpoint_pattern="/api/v1/no-service/{id}",
            required_roles=["admin"],
            required_permissions=[],
            allow_service_auth=False,
            description="No service auth allowed",
        )

        rbac.add_permission_rule(no_service_rule)

        result = rbac.check_permissions(service_user, "/api/v1/no-service/123")

        # Service should be denied even though it has service role
        assert result.success is False
        assert result.error_code == "AUTH_002"

    def test_permission_requirements_check(self, rbac):
        """Test permission requirements checking."""
        perm_rule = PermissionRule(
            endpoint_pattern="/api/v1/special/{id}",
            required_roles=[],
            required_permissions=["special:access"],
            allow_service_auth=True,
        )

        rbac.add_permission_rule(perm_rule)

        # User with required permission
        user_with_perm = UserContext(
            user_id="special123",
            email="special@example.com",
            roles=["viewer"],
            permissions=["special:access"],
        )

        result = rbac.check_permissions(user_with_perm, "/api/v1/special/123")
        assert result.success is True

        # User without required permission
        user_without_perm = UserContext(
            user_id="noperm123",
            email="noperm@example.com",
            roles=["viewer"],
            permissions=["read:projects"],
        )

        result = rbac.check_permissions(user_without_perm, "/api/v1/special/123")
        assert result.success is False
        assert result.error_code == "AUTH_002"
