# -*- coding: utf-8 -*-
"""
人口系统路由 — 列表查询、纳入布控
"""

from fastapi import APIRouter, Depends, Query
from pymysql.cursors import DictCursor

from app.dependencies import get_db, get_current_user
from models.import_models import PromoteRequest
from services.import_service import promote_to_young_peoples

router = APIRouter()


@router.get("/api/population")
def list_population(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    keyword: str = Query(None),
    promoted: int = Query(None),
    conn=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """人口记录列表（分页）。"""
    conditions = []
    params = []

    if keyword:
        conditions.append("(name LIKE %s OR id_card_number LIKE %s)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    if promoted is not None:
        conditions.append("promoted = %s")
        params.append(promoted)

    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""

    with conn.cursor(DictCursor) as cursor:
        cursor.execute(f"SELECT COUNT(*) AS cnt FROM population_info{where}", params)
        total = cursor.fetchone()["cnt"]

        offset = (page - 1) * per_page
        cursor.execute(
            f"SELECT * FROM population_info{where} ORDER BY created_at DESC LIMIT %s OFFSET %s",
            params + [per_page, offset],
        )
        items = cursor.fetchall()

    pages = (total + per_page - 1) // per_page
    return {
        "success": True,
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
        },
    }


@router.post("/api/import/population/promote")
def promote_population(
    body: PromoteRequest,
    conn=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """将人口记录纳入布控（写入 young_peoples）。"""
    result = promote_to_young_peoples(
        conn, body.id_card_numbers, body.control_category,
        current_user.get("id"),
    )
    return {"success": True, "data": result}
