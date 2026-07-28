from __future__ import annotations

import hmac
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from web_app.application.waf_state_use_cases import (
    MAX_SNAPSHOT_BYTES,
    read_waf_snapshot,
)
from web_app.config import get_settings
from web_app.infrastructure.database import get_db
from web_app.presentation.schemas.waf_enforcement import WafSnapshotResponse

logger = logging.getLogger(__name__)
router = APIRouter()
NO_STORE = {"Cache-Control": "no-store"}


def _snapshot_unavailable() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail="Snapshot unavailable",
        headers=NO_STORE,
    )


def verify_waf_state_sync_authorization(request: Request) -> None:
    settings = get_settings()
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if (
        scheme.lower() != "bearer"
        or not token
        or not hmac.compare_digest(token, settings.waf_state_sync_api_key)
    ):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer", "Cache-Control": "no-store"},
        )


@router.get("/internal/waf-enforcement/snapshot", response_model=WafSnapshotResponse)
async def waf_enforcement_snapshot(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    settings = get_settings()
    response.headers["Cache-Control"] = "no-store"
    if not settings.waf_state_sync_enabled or settings.app_env not in {
        "development",
        "testing",
    }:
        return JSONResponse(
            status_code=404,
            content={"detail": "Not found"},
            headers={"Cache-Control": "no-store"},
        )
    verify_waf_state_sync_authorization(request)
    try:
        payload = await read_waf_snapshot(db)
        response_model = WafSnapshotResponse.model_validate(payload)
        encoded = response_model.model_dump_json().encode("utf-8")
        if len(encoded) > MAX_SNAPSHOT_BYTES:
            raise ValueError("snapshot exceeds response size limit")
    except ValueError as exc:
        logger.warning("waf_snapshot_failed reason=%s", type(exc).__name__)
        raise _snapshot_unavailable() from None
    except Exception as exc:
        logger.error("waf_snapshot_failed reason=%s", type(exc).__name__)
        raise _snapshot_unavailable() from None
    logger.info(
        "waf_snapshot_served revision=%s entry_count=%s",
        response_model.revision,
        len(response_model.items),
    )
    return JSONResponse(
        content=response_model.model_dump(mode="json"),
        headers={"Cache-Control": "no-store"},
    )
