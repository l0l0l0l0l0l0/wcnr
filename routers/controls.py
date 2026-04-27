# -*- coding: utf-8 -*-
"""
布控管理路由 — 统计、列表、批量操作、导入、今日预警
"""

from fastapi import APIRouter, Depends, Query
from pymysql.cursors import DictCursor
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.dependencies import get_db, get_yp_columns
from app.utils import safe_get

router = APIRouter()


class BatchRevokeRequest(BaseModel):
    ids: List[str] = Field(..., min_length=1)
    reason: str = ""


class BatchDeleteRequest(BaseModel):
    ids: List[str] = Field(..., min_length=1)


class ImportItem(BaseModel):
    id_card: str = ""
    name: str = ""
    gender: str = ""
    age: Optional[str] = None
    ethnicity: str = ""
    control_library: str = "重点人员库"
    control_status: str = "布控中"
    sub_bureau: str = ""
    police_station: str = ""
    community: str = ""
    alias: str = ""
    phone: str = ""
    household_address: str = ""
    current_address: str = ""
    photo_url: Optional[str] = None


class ImportRequest(BaseModel):
    items: List[ImportItem] = Field(..., min_length=1)


@router.get("/api/control/stats")
def get_control_stats(conn=Depends(get_db), cols: set = Depends(get_yp_columns)):
    """布控统计：基于 young_peoples 表"""
    with conn.cursor(DictCursor) as cursor:
        today = datetime.now().strftime("%Y-%m-%d")

        cursor.execute("SELECT COUNT(*) AS cnt FROM young_peoples")
        total = cursor.fetchone()["cnt"]

        if "control_status" in cols:
            cursor.execute("SELECT COUNT(*) AS cnt FROM young_peoples WHERE control_status = '布控中' OR control_status IS NULL OR control_status = ''")
            controlling = cursor.fetchone()["cnt"]

            cursor.execute("SELECT COUNT(*) AS cnt FROM young_peoples WHERE control_status = '待审批'")
            pending = cursor.fetchone()["cnt"]

            cursor.execute("SELECT COUNT(*) AS cnt FROM young_peoples WHERE control_status = '已撤控'")
            revoked = cursor.fetchone()["cnt"]
        else:
            controlling = total
            pending = 0
            revoked = 0

        if "created_at" in cols:
            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM young_peoples WHERE DATE(created_at) = %s",
                (today,),
            )
            today_new = cursor.fetchone()["cnt"]
        else:
            today_new = 0

    return {
        "success": True,
        "data": {
            "total": total,
            "controlling": controlling,
            "pending": pending,
            "revoked": revoked,
            "today_new": today_new,
        },
    }


@router.get("/api/controls")
def get_controls(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    library: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    address: Optional[str] = Query(None),
    photo: Optional[str] = Query(None),
    conn=Depends(get_db),
    cols: set = Depends(get_yp_columns),
):
    """布控人员列表：基于 young_peoples 表"""
    with conn.cursor(DictCursor) as cursor:
        where_clauses = []
        params = []

        if library and "control_library" in cols:
            where_clauses.append("yp.control_library = %s")
            params.append(library)

        if status and "control_status" in cols:
            if status == "布控中":
                where_clauses.append("(yp.control_status = '布控中' OR yp.control_status IS NULL OR yp.control_status = '')")
            else:
                where_clauses.append("yp.control_status = %s")
                params.append(status)

        if keyword:
            name_col = "yp.name" if "name" in cols else "yp.id_card_number"
            where_clauses.append(f"({name_col} LIKE %s OR yp.id_card_number LIKE %s)")
            like_kw = f"%{keyword}%"
            params.extend([like_kw, like_kw])

        if address and "household_address" in cols:
            where_clauses.append("(yp.household_address LIKE %s OR yp.current_address LIKE %s)")
            like_addr = f"%{address}%"
            params.extend([like_addr, like_addr])

        if photo == "有照片":
            where_clauses.append("yp.person_face_url IS NOT NULL AND yp.person_face_url != '' AND yp.person_face_url != 'null'")
        elif photo == "无照片":
            where_clauses.append("(yp.person_face_url IS NULL OR yp.person_face_url = '' OR yp.person_face_url = 'null')")

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        cursor.execute(f"SELECT COUNT(*) AS cnt FROM young_peoples yp{where_sql}", params)
        total = cursor.fetchone()["cnt"]

        pages = max(1, (total + per_page - 1) // per_page)
        offset = (page - 1) * per_page

        order_col = "yp.created_at" if "created_at" in cols else "yp.id"
        sql = f"""
        SELECT yp.*,
            (SELECT MAX(cr.capture_time) FROM capture_records cr
             WHERE cr.person_id_card = yp.id_card_number
               AND cr.capture_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            ) AS latest_alert_time
        FROM young_peoples yp
        {where_sql}
        ORDER BY {order_col} DESC
        LIMIT %s OFFSET %s
        """
        cursor.execute(sql, params + [per_page, offset])
        rows = cursor.fetchall()

        items = []
        for r in rows:
            control_status = safe_get(r, "control_status", "布控中")
            if control_status in (None, "", "null", "--"):
                control_status = "布控中"

            items.append({
                "control_id": safe_get(r, "id_card_number", ""),
                "name": safe_get(r, "name", safe_get(r, "id_card_number", "--")),
                "id_card": safe_get(r, "id_card_number", "--"),
                "gender": safe_get(r, "gender", "--"),
                "age": r.get("age"),
                "ethnicity": safe_get(r, "ethnicity", "--"),
                "control_library": safe_get(r, "control_library", "重点人员库"),
                "control_status": control_status,
                "latest_alert_time": r.get("latest_alert_time").strftime("%Y-%m-%d %H:%M") if r.get("latest_alert_time") else "--",
                "sub_bureau": safe_get(r, "sub_bureau", "--"),
                "police_station": safe_get(r, "police_station", "--"),
                "community": safe_get(r, "community", "--"),
                "alias": safe_get(r, "alias", "--"),
                "phone": safe_get(r, "phone", "--"),
                "household_address": safe_get(r, "household_address", "--"),
                "current_address": safe_get(r, "current_address", "--"),
                "photo_url": r.get("person_face_url"),
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


@router.post("/api/control/batch_revoke")
def batch_revoke_control(body: BatchRevokeRequest, conn=Depends(get_db)):
    """批量撤控"""
    with conn.cursor() as cursor:
        placeholders = ",".join(["%s"] * len(body.ids))
        cursor.execute(
            f"UPDATE young_peoples SET control_status = '已撤控' WHERE id_card_number IN ({placeholders}) AND (control_status != '已撤控' OR control_status IS NULL)",
            body.ids,
        )
        updated = cursor.rowcount
        conn.commit()

    return {"success": True, "message": f"已成功撤控 {updated} 条记录", "data": {"updated": updated}}


@router.post("/api/control/batch_delete")
def batch_delete_control(body: BatchDeleteRequest, conn=Depends(get_db)):
    """批量删除"""
    with conn.cursor() as cursor:
        placeholders = ",".join(["%s"] * len(body.ids))
        cursor.execute(
            f"DELETE FROM young_peoples WHERE id_card_number IN ({placeholders})",
            body.ids,
        )
        deleted = cursor.rowcount
        conn.commit()

    return {"success": True, "message": f"已成功删除 {deleted} 条记录", "data": {"deleted": deleted}}


@router.post("/api/control/import")
def import_controls(body: ImportRequest, conn=Depends(get_db), cols: set = Depends(get_yp_columns)):
    """导入布控人员"""
    imported = 0
    with conn.cursor() as cursor:
        for item in body.items:
            insert_cols = ["id_card_number"]
            insert_vals = [item.id_card]
            updates = []

            optional_cols = [
                ("name", "name", ""), ("gender", "gender", ""), ("age", "age", None),
                ("ethnicity", "ethnicity", ""), ("control_library", "control_library", "重点人员库"),
                ("control_status", "control_status", "布控中"), ("sub_bureau", "sub_bureau", ""),
                ("police_station", "police_station", ""), ("community", "community", ""),
                ("alias", "alias", ""), ("phone", "phone", ""),
                ("household_address", "household_address", ""), ("current_address", "current_address", ""),
                ("person_face_url", "photo_url", None),
            ]

            for db_col, item_key, default in optional_cols:
                if db_col in cols:
                    insert_cols.append(db_col)
                    insert_vals.append(getattr(item, item_key, default))
                    if db_col != "id_card_number":
                        updates.append(f"{db_col} = VALUES({db_col})")

            placeholders = ",".join(["%s"] * len(insert_cols))
            col_names = ",".join(insert_cols)
            update_sql = ",".join(updates) if updates else "name = VALUES(name)"

            cursor.execute(
                f"INSERT INTO young_peoples ({col_names}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_sql}",
                insert_vals,
            )
            imported += 1
        conn.commit()

    return {"success": True, "message": f"成功导入 {imported} 条记录", "data": {"imported": imported}}


@router.get("/api/control/today")
def get_today_controls(conn=Depends(get_db)):
    """今日预警布控人员"""
    with conn.cursor(DictCursor) as cursor:
        cursor.execute("""
            SELECT yp.*,
                (SELECT MAX(cr.capture_time) FROM capture_records cr
                 WHERE cr.person_id_card = yp.id_card_number
                   AND cr.capture_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                ) AS latest_alert_time
            FROM young_peoples yp
            WHERE EXISTS (
                SELECT 1 FROM capture_records cr
                WHERE cr.person_id_card = yp.id_card_number
                  AND cr.capture_time >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            )
            ORDER BY latest_alert_time DESC
        """)
        rows = cursor.fetchall()

        items = []
        for r in rows:
            items.append({
                "control_id": safe_get(r, "id_card_number", ""),
                "name": safe_get(r, "name", safe_get(r, "id_card_number", "--")),
                "id_card": safe_get(r, "id_card_number", "--"),
                "gender": safe_get(r, "gender", "--"),
                "age": r.get("age"),
                "ethnicity": safe_get(r, "ethnicity", "--"),
                "control_library": safe_get(r, "control_library", "重点人员库"),
                "control_status": safe_get(r, "control_status", "布控中"),
                "latest_alert_time": r.get("latest_alert_time").strftime("%Y-%m-%d %H:%M") if r.get("latest_alert_time") else "--",
                "sub_bureau": safe_get(r, "sub_bureau", "--"),
                "police_station": safe_get(r, "police_station", "--"),
                "community": safe_get(r, "community", "--"),
                "alias": safe_get(r, "alias", "--"),
                "phone": safe_get(r, "phone", "--"),
                "household_address": safe_get(r, "household_address", "--"),
                "current_address": safe_get(r, "current_address", "--"),
                "photo_url": r.get("person_face_url"),
            })

    return {"success": True, "data": items}
