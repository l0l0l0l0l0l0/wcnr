# -*- coding: utf-8 -*-
"""
案件路由 — 列表查询、详情
"""

from fastapi import APIRouter, Depends, Query
from pymysql.cursors import DictCursor

from app.dependencies import get_db, get_current_user

router = APIRouter()


@router.get("/api/cases")
def list_cases(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    keyword: str = Query(None),
    case_type: str = Query(None),
    conn=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """案件列表（分页）。"""
    conditions = []
    params = []

    if keyword:
        conditions.append("(case_name LIKE %s OR case_number LIKE %s)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    if case_type:
        conditions.append("case_type = %s")
        params.append(case_type)

    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""

    with conn.cursor(DictCursor) as cursor:
        cursor.execute(f"SELECT COUNT(*) AS cnt FROM cases{where}", params)
        total = cursor.fetchone()["cnt"]

        offset = (page - 1) * per_page
        cursor.execute(
            f"SELECT * FROM cases{where} ORDER BY created_at DESC LIMIT %s OFFSET %s",
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


@router.get("/api/cases/{case_id}")
def case_detail(case_id: int, conn=Depends(get_db),
                current_user=Depends(get_current_user)):
    """案件详情（含涉案人员）。"""
    with conn.cursor(DictCursor) as cursor:
        cursor.execute("SELECT * FROM cases WHERE id = %s", (case_id,))
        case = cursor.fetchone()
        if not case:
            from app.exception_handlers import AppError
            raise AppError("案件不存在", status_code=404)

        cursor.execute(
            "SELECT id_card_number, person_name, person_source, role_in_case FROM case_persons WHERE case_id = %s",
            (case_id,),
        )
        persons = cursor.fetchall()

    case["persons"] = persons
    return {"success": True, "data": case}
