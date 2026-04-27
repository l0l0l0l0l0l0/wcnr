# -*- coding: utf-8 -*-
"""
认证服务 — JWT 生成/验证, 密码哈希
"""

from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
import bcrypt
from pymysql.cursors import DictCursor
import pymysql

from app.config import get_settings
from models.user import TokenData


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.jwt_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Optional[TokenData]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            return None
        return TokenData(username=username, role=role)
    except JWTError:
        return None


def authenticate_user(conn, username: str, password: str) -> Optional[dict]:
    """验证用户名密码，返回用户 dict 或 None。"""
    with conn.cursor(DictCursor) as cursor:
        cursor.execute(
            "SELECT id, username, password, real_name, role, police_station, is_active FROM users WHERE username = %s",
            (username,),
        )
        user = cursor.fetchone()

    if not user:
        return None
    if not user.get("is_active", 1):
        return None
    if not verify_password(password, user["password"]):
        return None
    return user
