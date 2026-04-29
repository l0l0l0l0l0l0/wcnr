# -*- coding: utf-8 -*-
"""
预警中心路由 — 统计、预警列表、图片代理
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse, JSONResponse
from pymysql.cursors import DictCursor
from datetime import datetime
from typing import Optional

from app.dependencies import get_db
import httpx

router = APIRouter()


@router.get("/api/stats")
def get_stats(conn=Depends(get_db)):
    """预警统计：基于 capture_records 表"""
    with conn.cursor(DictCursor) as cursor:
        today = datetime.now().strftime("%Y-%m-%d")

        cursor.execute("SELECT COUNT(*) AS cnt FROM capture_records")
        history_total = cursor.fetchone()["cnt"]

        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM capture_records WHERE DATE(capture_time) = %s",
            (today,),
        )
        today_total = cursor.fetchone()["cnt"]

        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM capture_records WHERE DATE(capture_time) = %s AND is_processed = 0",
            (today,),
        )
        pending_sign = cursor.fetchone()["cnt"]

        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM capture_records WHERE DATE(capture_time) = %s AND is_processed = 1",
            (today,),
        )
        pending_feedback = cursor.fetchone()["cnt"]

        cursor.execute(
            "SELECT COUNT(*) AS cnt FROM capture_records WHERE DATE(capture_time) = %s AND is_processed = 2",
            (today,),
        )
        feedback_done = cursor.fetchone()["cnt"]

    return {
        "success": True,
        "data": {
            "history_total": history_total,
            "today_total": today_total,
            "pending_sign": pending_sign,
            "pending_feedback": pending_feedback,
            "feedback_done": feedback_done,
        },
    }


@router.get("/api/alerts")
def get_alerts(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    camera_type: Optional[str] = Query(None),
    conn=Depends(get_db),
):
    """预警列表：capture_records LEFT JOIN young_peoples"""
    with conn.cursor(DictCursor) as cursor:
        where_clauses = []
        params = []

        if keyword:
            where_clauses.append("(cr.person_id_card LIKE %s OR cr.camera_name LIKE %s OR cr.plate_no LIKE %s)")
            like_kw = f"%{keyword}%"
            params.extend([like_kw, like_kw, like_kw])

        if status:
            status_map = {"待签收": "0", "待反馈": "1", "已反馈": "2", "已签收": "3"}
            if status in status_map:
                where_clauses.append("cr.is_processed = %s")
                params.append(status_map[status])

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        cursor.execute(f"SELECT COUNT(*) AS cnt FROM capture_records cr{where_sql}", params)
        total = cursor.fetchone()["cnt"]

        pages = max(1, (total + per_page - 1) // per_page)
        offset = (page - 1) * per_page

        sql = f"""
        SELECT cr.*, yp.name AS person_name, yp.control_category
        FROM capture_records cr
        LEFT JOIN young_peoples yp ON cr.person_id_card = yp.id_card_number
        {where_sql}
        ORDER BY cr.capture_time DESC
        LIMIT %s OFFSET %s
        """
        cursor.execute(sql, params + [per_page, offset])
        rows = cursor.fetchall()

        status_labels = {0: "待签收", 1: "待反馈", 2: "已反馈", 3: "已签收"}
        items = []
        for r in rows:
            sim = r.get("similarity")
            if sim is not None:
                sim = round(float(sim) * 100, 1) if float(sim) <= 1 else round(float(sim), 1)
            else:
                sim = 0

            items.append({
                "id": r.get("capture_id", ""),
                "name": r.get("person_name") or r.get("person_id_card", ""),
                "person_id_card": r.get("person_id_card") or "",
                "similarity": sim,
                "time": r.get("capture_time").strftime("%Y-%m-%d %H:%M:%S") if r.get("capture_time") else "",
                "location": r.get("camera_name", ""),
                "camera": r.get("camera_name", ""),
                "type": "车辆" if r.get("plate_no") else "人脸",
                "status": status_labels.get(r.get("is_processed", 0), "待签收"),
                "person_tag": r.get("control_category") or "重点人员",
                "face_pic_url": r.get("face_pic_url"),
                "bkg_url": r.get("bkg_url"),
                "person_face_url": r.get("person_face_url"),
            })

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


@router.get("/proxy-pic")
async def proxy_pic(url: str = Query(..., description="Image URL to proxy")):
    """代理图片请求，解决跨域问题"""
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "http://71.196.10.34/",
    }

    async with httpx.AsyncClient(verify=False, timeout=15) as client:
        resp = await client.get(url, headers=headers)
        return StreamingResponse(
            resp.aiter_bytes(1024),
            media_type=resp.headers.get("content-type", "image/jpeg"),
        )
