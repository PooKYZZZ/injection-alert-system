import secrets

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from web_app.config import get_settings

_bearer_scheme = HTTPBearer(auto_error=False)
_UNAUTHORIZED = HTTPException(
    status_code=401,
    detail="Unauthorized",
    headers={"WWW-Authenticate": "Bearer"},
)


async def verify_internal_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> None:
    settings = get_settings()
    
    # Skip auth in development mode if no API key is configured
    if settings.is_development and not settings.api_secret_key:
        return
    
    if credentials is None:
        raise _UNAUTHORIZED

    if credentials.scheme.lower() != "bearer":
        raise _UNAUTHORIZED

    api_secret_key = settings.api_secret_key
    if not api_secret_key:
        raise _UNAUTHORIZED

    if not secrets.compare_digest(credentials.credentials, api_secret_key):
        raise _UNAUTHORIZED
