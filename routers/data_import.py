# -*- coding: utf-8 -*-
"""
数据导入路由 — 人口/案件上传、确认、预览、日志
"""

from fastapi import APIRouter, Depends, UploadFile, File, Query
from pymysql.cursors import DictCursor

from app.dependencies import get_db, get_current_user
from app.exception_handlers import AppError
from models.import_models import ImportConfirmRequest
from services.import_service import (
    upload_population,
    confirm_population_import,
    upload_cases,
    confirm_case_import,
    MAX_FILE_SIZE,
)

router = APIRouter()


@router.post("/api/import/population/upload")
async def population_upload(
    file: UploadFile = File(...),
    conn=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """上传人口系统 Excel/CSV，解析入库暂存，返回预览。"""
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise AppError(f"文件大小超过限制（最大 {MAX_FILE_SIZE // 1024 // 1024} MB）")

    result = upload_population(
        conn, content, file.filename or "unknown.xlsx",
        current_user.get("id"), current_user.get("real_name"),
    )
    return {"success": True, "data": result}


@router.post("/api/import/population/confirm")
def population_confirm(
    body: ImportConfirmRequest,
    conn=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """确认人口数据导入：staging → population_info。"""
    result = confirm_population_import(conn, body.import_log_id,
                                       body.skip_invalid, body.skip_duplicate)
    return {"success": True, "data": result}


@router.get("/api/import/population/staging/{log_id}")
def population_staging(log_id: int, conn=Depends(get_db),
                       current_user=Depends(get_current_user)):
    """查看人口数据暂存。"""
    with conn.cursor(DictCursor) as cursor:
        cursor.execute(
            "SELECT * FROM population_staging WHERE import_log_id = %s ORDER BY row_number",
            (log_id,),
        )
        rows = cursor.fetchall()
    return {"success": True, "data": rows}


@router.post("/api/import/cases/upload")
async def cases_upload(
    file: UploadFile = File(...),
    conn=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """上传警综系统 Excel/CSV，解析入库暂存，返回预览。"""
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise AppError(f"文件大小超过限制（最大 {MAX_FILE_SIZE // 1024 // 1024} MB）")

    result = upload_cases(
        conn, content, file.filename or "unknown.xlsx",
        current_user.get("id"), current_user.get("real_name"),
    )
    return {"success": True, "data": result}


@router.post("/api/import/cases/confirm")
def cases_confirm(
    body: ImportConfirmRequest,
    conn=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """确认案件数据导入：staging → cases + case_persons。"""
    result = confirm_case_import(conn, body.import_log_id,
                                 body.skip_invalid, body.skip_duplicate)
    return {"success": True, "data": result}


@router.get("/api/import/cases/staging/{log_id}")
def cases_staging(log_id: int, conn=Depends(get_db),
                  current_user=Depends(get_current_user)):
    """查看案件数据暂存。"""
    with conn.cursor(DictCursor) as cursor:
        cursor.execute(
            "SELECT * FROM case_staging WHERE import_log_id = %s ORDER BY row_number",
            (log_id,),
        )
        rows = cursor.fetchall()
    return {"success": True, "data": rows}


@router.get("/api/import/logs")
def import_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    source_system: str = Query(None),
    status: str = Query(None),
    conn=Depends(get_db),
    current_user=Depends(get_current_user),
):
    """查看导入日志列表。"""
    conditions = []
    params = []

    if source_system:
        conditions.append("source_system = %s")
        params.append(source_system)
    if status:
        conditions.append("status = %s")
        params.append(status)

    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""

    with conn.cursor(DictCursor) as cursor:
        cursor.execute(f"SELECT COUNT(*) AS cnt FROM data_import_logs{where}", params)
        total = cursor.fetchone()["cnt"]

        offset = (page - 1) * per_page
        cursor.execute(
            f"SELECT * FROM data_import_logs{where} ORDER BY created_at DESC LIMIT %s OFFSET %s",
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
