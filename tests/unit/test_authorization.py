import json
from pathlib import Path

import pytest

from web_app.domain.authorization import (
    ROLE_HIERARCHY,
    ROLE_PERMISSIONS,
    Permission,
    UserRole,
    parse_user_role,
    role_at_least,
    role_has_permission,
)


def test_role_hierarchy_is_ordered_from_viewer_to_owner() -> None:
    assert ROLE_HIERARCHY == (
        UserRole.VIEWER,
        UserRole.ANALYST,
        UserRole.ADMIN,
        UserRole.OWNER,
    )
    assert role_at_least(UserRole.OWNER, UserRole.ADMIN)
    assert not role_at_least(UserRole.ADMIN, UserRole.OWNER)


@pytest.mark.parametrize("role", list(UserRole))
def test_only_owner_has_ml_permissions(role: UserRole) -> None:
    ml_permissions = {
        Permission.ML_HEALTH_READ,
        Permission.ML_MODEL_READ,
        Permission.ML_MODEL_RUN,
        Permission.ML_MODEL_APPROVE,
        Permission.ML_MODEL_DEPLOY,
    }

    for permission in ml_permissions:
        assert role_has_permission(role, permission) is (role is UserRole.OWNER)


@pytest.mark.parametrize("role", list(UserRole))
def test_training_feedback_management_is_owner_only(role: UserRole) -> None:
    assert role_has_permission(role, Permission.TRAINING_FEEDBACK_MANAGE) is (
        role is UserRole.OWNER
    )


def test_owner_inherits_every_existing_permission() -> None:
    assert ROLE_PERMISSIONS[UserRole.OWNER] == frozenset(Permission)


def test_python_permission_matrix_matches_shared_frontend_contract() -> None:
    matrix_path = (
        Path(__file__).parents[1] / "contracts" / "role-permission-matrix.json"
    )
    expected = json.loads(matrix_path.read_text(encoding="utf-8"))

    assert set(expected) == {role.value for role in UserRole}
    for role in UserRole:
        assert {permission.value for permission in ROLE_PERMISSIONS[role]} == set(
            expected[role.value]
        )
    assert {permission.value for permission in Permission} == {
        permission for permissions in expected.values() for permission in permissions
    }


def test_traffic_export_is_read_only_for_owner_admin_and_analyst() -> None:
    for role in (UserRole.OWNER, UserRole.ADMIN, UserRole.ANALYST):
        assert role_has_permission(role, Permission.TRAFFIC_EXPORT)
    assert not role_has_permission(UserRole.VIEWER, Permission.TRAFFIC_EXPORT)


def test_unknown_roles_fail_closed() -> None:
    assert parse_user_role("not-a-role") is None
    assert not role_has_permission("not-a-role", Permission.ALERTS_READ)
    assert not role_has_permission("not-a-role", Permission.TRAINING_FEEDBACK_MANAGE)
    assert not role_has_permission(None, Permission.ML_MODEL_READ)
