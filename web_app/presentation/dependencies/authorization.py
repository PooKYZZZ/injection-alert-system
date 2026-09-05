"""Presentation dependencies for trusted BFF actor authorization."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import HTTPException, Request

from web_app.application.label_review_use_case import ReviewerContext
from web_app.domain.authorization import (
    Permission,
    parse_user_role,
    role_has_permission,
)


def get_reviewer_context(request: Request) -> ReviewerContext:
    """Read and validate identity asserted by the trusted server-side BFF."""
    reviewer_id = request.headers.get("X-Reviewer-Id", "").strip()
    reviewer_role = parse_user_role(request.headers.get("X-Reviewer-Role", ""))
    if not reviewer_id or reviewer_role is None:
        raise HTTPException(status_code=403, detail="Reviewer context required")
    return ReviewerContext(
        reviewer_id=reviewer_id,
        reviewer_role=reviewer_role.value,
    )


def require_reviewer_permission(
    permission: Permission,
) -> Callable[[Request], ReviewerContext]:
    """Build a dependency that requires one permission for the BFF actor."""

    def dependency(request: Request) -> ReviewerContext:
        actor = get_reviewer_context(request)
        if not role_has_permission(actor.reviewer_role, permission):
            raise HTTPException(status_code=403, detail="Permission required")
        return actor

    return dependency


__all__ = [
    "get_reviewer_context",
    "require_reviewer_permission",
]
