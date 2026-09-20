from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session

from app.model.models import User
from app.session import get_db


def get_current_user_id(x_user_id: int = Header(..., alias="X-User-Id")) -> int:
    """简单用请求头模拟用户，后续可换成 JWT"""
    return x_user_id

def get_or_create_user(user_id: int, db: Session = Depends(get_db)) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(id=user_id, username=f"user_{user_id}")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user