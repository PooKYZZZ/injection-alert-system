"""Domain authorization vocabulary and the application's role hierarchy."""

from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    ANALYST = "ANALYST"
    VIEWER = "VIEWER"


class Permission(StrEnum):
    ALERTS_READ = "alerts:read"
    ALERTS_TRIAGE = "alerts:triage"
    ALERTS_ACTION_UPDATE = "alerts:action:update"
    STATS_READ = "stats:read"
    ML_HEALTH_READ = "ml-health:read"
    ML_MODEL_READ = "ml-model:read"
    ML_MODEL_RUN = "ml-model:run"
    ML_MODEL_APPROVE = "ml-model:approve"
    ML_MODEL_DEPLOY = "ml-model:deploy"
    ACCOUNTS_READ = "accounts:read"
    ACCOUNTS_MANAGE = "accounts:manage"
    MFA_ENROLLMENT = "mfa:enrollment"


# Lowest to highest privilege. Authorization decisions should use permissions;
# this order is for role hierarchy and safe role-assignment rules.
ROLE_HIERARCHY: tuple[UserRole, ...] = (
    UserRole.VIEWER,
    UserRole.ANALYST,
    UserRole.ADMIN,
    UserRole.OWNER,
)

ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.VIEWER: frozenset(
        {
            Permission.ALERTS_READ,
            Permission.STATS_READ,
        }
    ),
    UserRole.ANALYST: frozenset(
        {
            Permission.ALERTS_READ,
            Permission.ALERTS_TRIAGE,
            Permission.STATS_READ,
            Permission.MFA_ENROLLMENT,
        }
    ),
    UserRole.ADMIN: frozenset(
        {
            Permission.ALERTS_READ,
            Permission.ALERTS_TRIAGE,
            Permission.ALERTS_ACTION_UPDATE,
            Permission.STATS_READ,
            Permission.ACCOUNTS_READ,
            Permission.ACCOUNTS_MANAGE,
            Permission.MFA_ENROLLMENT,
        }
    ),
    UserRole.OWNER: frozenset(Permission),
}


def parse_user_role(value: object) -> UserRole | None:
    if not isinstance(value, str):
        return None
    try:
        return UserRole(value.strip().upper())
    except ValueError:
        return None


def role_has_permission(role: object, permission: Permission | str) -> bool:
    parsed_role = parse_user_role(role)
    if parsed_role is None:
        return False
    try:
        parsed_permission = Permission(permission)
    except ValueError:
        return False
    return parsed_permission in ROLE_PERMISSIONS[parsed_role]


def role_at_least(role: object, minimum_role: UserRole) -> bool:
    parsed_role = parse_user_role(role)
    if parsed_role is None:
        return False
    return ROLE_HIERARCHY.index(parsed_role) >= ROLE_HIERARCHY.index(minimum_role)


__all__ = [
    "Permission",
    "ROLE_HIERARCHY",
    "ROLE_PERMISSIONS",
    "UserRole",
    "parse_user_role",
    "role_at_least",
    "role_has_permission",
]
