from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db
from app.security.auth import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not user.is_active or not user.password_hash or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials", headers={"WWW-Authenticate": "Bearer"})
    return {
        "access_token": create_access_token(user_id=user.id, tenant_id=user.tenant_id, role=user.role),
        "token_type": "bearer",
        "expires_in": 60 *  settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    }
