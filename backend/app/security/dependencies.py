from fastapi import Depends, Header, HTTPException
from app.core.config import settings


def get_tenant_id(x_tenant_id: str | None = Header(default=None)) -> str:
    if settings.ENABLE_AUTH:
        if not x_tenant_id:
            raise HTTPException(status_code=401, detail="Tenant context required")
        return x_tenant_id
    return x_tenant_id or "default-tenant"


def get_user_id(x_user_id: str | None = Header(default=None)) -> str:
    """Return the user identity from the existing security context.

    Development mode keeps a stable anonymous identity for backward compatibility.
    Production authentication should derive this value from the verified access token,
    not from an untrusted client-supplied header.
    """
    if settings.ENABLE_AUTH and not x_user_id:
        raise HTTPException(status_code=401, detail="User context required")
    return x_user_id or "anonymous"


def require_role(*allowed: str):
    def dependency(x_role: str | None = Header(default=None)) -> str:
        role = x_role or "admin"
        if settings.ENABLE_AUTH and role not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return role
    return dependency
