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


def test_unknown_roles_fail_closed() -> None:
    assert parse_user_role("not-a-role") is None
    assert not role_has_permission("not-a-role", Permission.ALERTS_READ)
    assert not role_has_permission("not-a-role", Permission.TRAINING_FEEDBACK_MANAGE)
    assert not role_has_permission(None, Permission.ML_MODEL_READ)
