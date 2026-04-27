# -*- coding: utf-8 -*-
"""
FastAPI 依赖注入
"""

from typing import Generator, Optional
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pymysql.cursors import DictCursor
import pymysql

from app.config import Settings, get_settings
from app.exception_handlers import AppError
from services.schema_cache import get_yp_columns as _get_yp_columns
from services.auth import decode_access_token

security = HTTPBearer(auto_error=False)


def get_db(settings: Settings = Depends(get_settings)) -> Generator:
    """提供 pymysql 连接，请求结束后自动关闭。"""
    conn = pymysql.connect(**settings.db_config)
    try:
        yield conn
    finally:
        conn.close()


def get_yp_columns(conn=Depends(get_db)) -> set:
    """提供 young_peoples 列缓存。"""
    return _get_yp_columns(conn)


def get_dify_modules() -> dict:
    """提供已加载的 Dify 模块字典。"""
    from services.dify_loader import load_dify_modules
    return load_dify_modules()


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    settings: Settings = Depends(get_settings),
) -> dict:
    """解析 JWT token 并返回当前用户信息。"""
    if credentials is None:
        raise AppError("未提供认证凭据", status_code=401)

    token_data = decode_access_token(credentials.credentials)
    if token_data is None or token_data.username is None:
        raise AppError("无效或已过期的 token", status_code=401)

    # 仅在 token 有效时才打开 DB 连接
    conn = pymysql.connect(**settings.db_config)
    try:
        with conn.cursor(DictCursor) as cursor:
            cursor.execute(
                "SELECT id, username, real_name, role, police_station, is_active FROM users WHERE username = %s",
                (token_data.username,),
            )
            user = cursor.fetchone()
    finally:
        conn.close()

    if not user or not user.get("is_active", 1):
        raise AppError("用户不存在或已停用", status_code=401)

    return user
