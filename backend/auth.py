"""
Shared bearer-token auth dependency for every /api/* route.

This is intentionally the simplest thing that closes the "anyone on the
network can use the API" hole: a static token -> identity map, checked with
a constant-time comparison. It's structured so swapping in JWT/OAuth/session
auth later only means replacing get_current_identity()'s body - callers
already just depend on "give me the caller's identity string".
"""
import hmac

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import API_TOKENS

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_identity(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> str:
    """FastAPI dependency: returns the caller's identity or raises 401/503."""
    if not API_TOKENS:
        # Fail closed rather than silently accepting every request when
        # nobody has configured MJ_API_TOKENS yet.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication is not configured on this server (set MJ_API_TOKENS).",
        )

    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    supplied = credentials.credentials
    for known_token, identity in API_TOKENS.items():
        if hmac.compare_digest(known_token, supplied):
            return identity

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid bearer token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
