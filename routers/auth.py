# -*- coding: utf-8 -*-
"""
认证路由 — 登录、注册、刷新 token
"""

from fastapi import APIRouter, Depends, Response
from pymysql.cursors import DictCursor
import pymysql

from app.dependencies import get_db, get_current_user
from app.exception_handlers import AppError
from models.user import UserLogin, UserCreate, Token, UserResponse
from services.auth import hash_password, authenticate_user, create_access_token, verify_password
from app.config import get_settings

router = APIRouter()


@router.post("/api/auth/login", response_model=Token)
def login(body: UserLogin, response: Response, conn=Depends(get_db)):
    user = authenticate_user(conn, body.username, body.password)
    if not user:
        raise AppError("用户名或密码错误", status_code=401)

    token = create_access_token(data={"sub": user["username"], "role": user["role"]})
    settings = get_settings()
    response.set_cookie(
        "access_token", token,
        httponly=False,
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
    )
    return Token(access_token=token)


@router.post("/api/auth/logout")
def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"success": True, "message": "已退出登录"}


@router.post("/api/auth/register", response_model=UserResponse)
def register(body: UserCreate, conn=Depends(get_db), current_user=Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise AppError("仅管理员可注册新用户", status_code=403)

    with conn.cursor(DictCursor) as cursor:
        cursor.execute("SELECT id FROM users WHERE username = %s", (body.username,))
        if cursor.fetchone():
            raise AppError("用户名已存在", status_code=409)

        hashed = hash_password(body.password)
        cursor.execute(
            "INSERT INTO users (username, password, real_name, role, police_station) VALUES (%s, %s, %s, %s, %s)",
            (body.username, hashed, body.real_name, body.role, body.police_station),
        )
        conn.commit()
        user_id = cursor.lastrowid

        cursor.execute(
            "SELECT id, username, real_name, role, police_station, is_active, created_at FROM users WHERE id = %s",
            (user_id,),
        )
        return cursor.fetchone()


@router.post("/api/auth/refresh", response_model=Token)
def refresh_token(current_user=Depends(get_current_user)):
    token = create_access_token(data={"sub": current_user["username"], "role": current_user["role"]})
    return Token(access_token=token)
