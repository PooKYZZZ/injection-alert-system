import logging
import secrets

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from web_app.config import get_settings

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)
_UNAUTHORIZED = HTTPException(
    status_code=401,
    detail="Unauthorized",
    headers={"WWW-Authenticate": "Bearer"},
)
_NO_API_KEY = HTTPException(
    status_code=500,
    detail="Internal server configuration error: API_SECRET_KEY not configured",
)


async def verify_internal_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> None:
    settings = get_settings()
    
    # Auth is always required in production and staging environments
    if settings.is_production or settings.is_staging:
        if not settings.api_secret_key:
            # In production/staging without API key, deny access (don't reveal config issue)
            logger.error(
                "API_SECRET_KEY is not configured for production/staging environment. "
                "Internal endpoints are protected and require a valid API_SECRET_KEY."
            )
            raise _UNAUTHORIZED
        
        # Verify credentials are provided
        if credentials is None:
            raise _UNAUTHORIZED

        if credentials.scheme.lower() != "bearer":
            raise _UNAUTHORIZED

        if not secrets.compare_digest(credentials.credentials, settings.api_secret_key):
            raise _UNAUTHORIZED
        return
    
    # Development mode: allow auth bypass only if no API key is explicitly configured
    # This is intentional for local development ergonomics
    if settings.is_development and not settings.api_secret_key:
        logger.warning(
            "API_SECRET_KEY not configured - auth bypass enabled for development. "
            "This is intentional for local development only. "
            "Ensure API_SECRET_KEY is set in production/staging environments."
        )
        return
    
    # Development mode with API key configured: require auth
    if credentials is None:
        raise _UNAUTHORIZED

    if credentials.scheme.lower() != "bearer":
        raise _UNAUTHORIZED

    if not settings.api_secret_key:
        raise _NO_API_KEY

    if not secrets.compare_digest(credentials.credentials, settings.api_secret_key):
        raise _UNAUTHORIZED


async def verify_waf_ingest_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> None:
    settings = get_settings()
    key = settings.waf_ingest_api_key

    if not key:
        raise _UNAUTHORIZED

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _UNAUTHORIZED

    if not secrets.compare_digest(credentials.credentials, key):
        raise _UNAUTHORIZED


async def verify_enforcement_check_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> None:
    """Verify the dedicated server-to-server enforcement check credential."""
    key = get_settings().enforcement_check_api_key
    if not key:
        raise _UNAUTHORIZED
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _UNAUTHORIZED
    if not secrets.compare_digest(credentials.credentials, key):
        raise _UNAUTHORIZED
