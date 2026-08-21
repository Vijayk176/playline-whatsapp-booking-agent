from sqlalchemy.orm import Session
from fastapi import Request, HTTPException, status
from app.models.models import User
from app.utils.security import hash_password, verify_password, create_access_token, decode_access_token
from app.config import settings


def ensure_default_admin(db: Session):
    user = db.query(User).filter(User.username == settings.admin_username).first()
    if not user:
        user = User(username=settings.admin_username, hashed_password=hash_password(settings.admin_password))
        db.add(user)
        db.commit()


def authenticate_admin(db: Session, username: str, password: str) -> bool:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return False
    return verify_password(password, user.hashed_password)


def get_current_admin(request: Request) -> str:
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/admin/login"})
    username = decode_access_token(token)
    if not username:
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/admin/login"})
    return username
