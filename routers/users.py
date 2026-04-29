# -*- coding: utf-8 -*-
"""
用户管理路由 — CRUD
"""

from fastapi import APIRouter, Depends, Query
from pymysql.cursors import DictCursor
from typing import Optional

from app.dependencies import get_db, get_current_user
from app.exception_handlers import AppError
from app.utils import safe_get
from models.user import UserUpdate, UserSelfUpdate, UserResponse
from services.auth import hash_password, verify_password

router = APIRouter()


@router.get("/api/users", response_model=dict)
def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = Query(None),
    conn=Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user["role"] != "admin":
        raise AppError("仅管理员可查看用户列表", status_code=403)

    with conn.cursor(DictCursor) as cursor:
        where = ""
        params = []
        if keyword:
            where = "WHERE (username LIKE %s OR real_name LIKE %s)"
            like = f"%{keyword}%"
            params = [like, like]

        cursor.execute(f"SELECT COUNT(*) AS cnt FROM users {where}", params)
        total = cursor.fetchone()["cnt"]
        pages = max(1, (total + per_page - 1) // per_page)
        offset = (page - 1) * per_page

        cursor.execute(
            f"SELECT id, username, real_name, role, police_station, is_active, created_at FROM users {where} ORDER BY id DESC LIMIT %s OFFSET %s",
            params + [per_page, offset],
        )
        items = []
        for r in cursor.fetchall():
            if r.get("created_at"):
                r["created_at"] = r["created_at"].strftime("%Y-%m-%d %H:%M:%S")
            items.append(r)

    return {"success": True, "data": {"items": items, "total": total, "page": page, "per_page": per_page, "pages": pages}}


@router.get("/api/users/me", response_model=dict)
def get_me(current_user=Depends(get_current_user)):
    return {
        "success": True,
        "data": {
            "id": current_user["id"],
            "username": current_user["username"],
            "real_name": current_user["real_name"],
            "role": current_user["role"],
            "police_station": current_user.get("police_station"),
            "is_active": current_user["is_active"],
        },
    }


@router.put("/api/users/me", response_model=dict)
def update_me(
    body: UserSelfUpdate,
    conn=Depends(get_db),
    current_user=Depends(get_current_user),
):
    updates = []
    params = []
    if body.real_name is not None:
        updates.append("real_name = %s")
        params.append(body.real_name)
    if body.password is not None:
        if not body.old_password:
            raise AppError("修改密码需提供原密码", status_code=400)
        with conn.cursor(DictCursor) as cursor:
            cursor.execute("SELECT password FROM users WHERE id = %s", (current_user["id"],))
            row = cursor.fetchone()
        if not row or not verify_password(body.old_password, row["password"]):
            raise AppError("原密码错误", status_code=400)
        updates.append("password = %s")
        params.append(hash_password(body.password))

    if updates:
        params.append(current_user["id"])
        with conn.cursor() as cursor:
            cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = %s", params)
            conn.commit()

    return {"success": True, "message": "信息更新成功"}


@router.put("/api/users/{user_id}", response_model=dict)
def update_user(
    user_id: int,
    body: UserUpdate,
    conn=Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user["role"] != "admin":
        raise AppError("仅管理员可修改用户", status_code=403)

    with conn.cursor(DictCursor) as cursor:
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            raise AppError("用户不存在", status_code=404)

    updates = []
    params = []
    for field in ("real_name", "role", "police_station", "is_active"):
        val = getattr(body, field, None)
        if val is not None:
            updates.append(f"{field} = %s")
            params.append(val)

    if updates:
        params.append(user_id)
        with conn.cursor() as cursor:
            cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = %s", params)
            conn.commit()

    return {"success": True, "message": "用户更新成功"}


@router.delete("/api/users/{user_id}", response_model=dict)
def delete_user(
    user_id: int,
    conn=Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user["role"] != "admin":
        raise AppError("仅管理员可停用用户", status_code=403)

    with conn.cursor() as cursor:
        cursor.execute("UPDATE users SET is_active = 0 WHERE id = %s", (user_id,))
        if cursor.rowcount == 0:
            raise AppError("用户不存在", status_code=404)
        conn.commit()

    return {"success": True, "message": "用户已停用"}
