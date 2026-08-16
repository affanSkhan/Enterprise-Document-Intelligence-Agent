from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import User
from app.db.session import get_db
from app.security.auth import decode_access_token

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: str
    tenant_id: str
    role: str


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> CurrentUser:
    if not settings.ENABLE_AUTH:
        return CurrentUser(id="dev-user", tenant_id="default-tenant", role="admin")
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
    try:
        claims = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc), headers={"WWW-Authenticate": "Bearer"}) from exc
    user = db.get(User, claims["sub"])
    if not user or not user.is_active or user.tenant_id != claims["tenant_id"] or user.role != claims["role"]:
        raise HTTPException(status_code=401, detail="Invalid user session", headers={"WWW-Authenticate": "Bearer"})
    return CurrentUser(id=user.id, tenant_id=user.tenant_id, role=user.role)


def get_tenant_id(current: CurrentUser = Depends(get_current_user), x_tenant_id: str | None = Header(default=None)) -> str:
    if settings.ENABLE_AUTH and x_tenant_id and x_tenant_id != current.tenant_id:
        raise HTTPException(status_code=403, detail="Cross-tenant access denied")
    return current.tenant_id if settings.ENABLE_AUTH else (x_tenant_id or current.tenant_id)


def require_role(*allowed: str):
    def dependency(current: CurrentUser = Depends(get_current_user)) -> str:
        if current.role not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current.role
    return dependency
