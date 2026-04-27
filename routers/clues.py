# -*- coding: utf-8 -*-
"""
线索管理路由 — CRUD + 统计
消除原 clue_routes.py 的循环导入 (from app import app)
"""

from fastapi import APIRouter, Depends, Query
from pymysql.cursors import DictCursor
from datetime import datetime
from typing import Optional

from app.dependencies import get_db

router = APIRouter()


@router.get("/api/clues")
def get_clues(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    conn=Depends(get_db),
):
    """获取线索列表（按线索编号分组）"""
    with conn.cursor(DictCursor) as cursor:
        distinct_sql = "SELECT DISTINCT clue_number FROM clues WHERE 1=1"
        params = []

        if status:
            distinct_sql += " AND status = %s"
            params.append(status)

        if keyword:
            distinct_sql += " AND (clue_number LIKE %s OR title LIKE %s OR responsible_officer LIKE %s)"
            params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])

        count_sql = "SELECT COUNT(*) as total FROM (" + distinct_sql + ") as count_table"
        cursor.execute(count_sql, params)
        total_result = cursor.fetchone()
        total_count = total_result["total"] if total_result else 0

        distinct_sql += " ORDER BY clue_number DESC LIMIT %s OFFSET %s"
        params.extend([page_size, (page - 1) * page_size])
        cursor.execute(distinct_sql, params)
        clue_numbers = [row["clue_number"] for row in cursor.fetchall()]

        clues = []
        if clue_numbers:
            placeholders = ", ".join(["%s"] * len(clue_numbers))
            sql = f"""
                SELECT
                    id, clue_number, title, content_cr_id,
                    issue_date, deadline, status,
                    responsible_officer, created_at, updated_at
                FROM clues
                WHERE clue_number IN ({placeholders})
                ORDER BY clue_number, created_at DESC
            """
            cursor.execute(sql, clue_numbers)
            all_records = cursor.fetchall()

            seen_clue_numbers = set()
            for record in all_records:
                if record["clue_number"] not in seen_clue_numbers:
                    seen_clue_numbers.add(record["clue_number"])
                    if record.get("created_at"):
                        record["created_at"] = record["created_at"].strftime("%Y-%m-%d %H:%M:%S")
                    if record.get("updated_at"):
                        record["updated_at"] = record["updated_at"].strftime("%Y-%m-%d %H:%M:%S")
                    if record.get("issue_date"):
                        record["issue_date"] = record["issue_date"].strftime("%Y-%m-%d")
                    if record.get("deadline"):
                        record["deadline"] = record["deadline"].strftime("%Y-%m-%d")
                    clues.append(record)

    return {"code": 200, "data": clues, "total": total_count}


@router.post("/api/clues")
def create_clue(
    body: dict,
    conn=Depends(get_db),
):
    """创建线索"""
    clue_number = body.get("clue_number")
    title = body.get("title")
    content_cr_id = body.get("content_cr_id")
    issue_date = body.get("issue_date")
    deadline = body.get("deadline")
    status = body.get("status", "pending")
    responsible_officer = body.get("responsible_officer")

    if not clue_number or not title or not issue_date:
        return {"code": 400, "message": "线索编号、标题和下发日期为必填项"}

    with conn.cursor(DictCursor) as cursor:
        now = datetime.now()
        sql = """
            INSERT INTO clues (clue_number, title, content_cr_id, issue_date, deadline, status, responsible_officer, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (clue_number, title, content_cr_id, issue_date, deadline, status, responsible_officer, now, now))
        conn.commit()
        clue_id = cursor.lastrowid

    return {"code": 200, "message": "线索创建成功", "data": {"id": clue_id}}


@router.get("/api/clues/statistics")
def get_clues_statistics(conn=Depends(get_db)):
    """获取线索统计数据"""
    with conn.cursor(DictCursor) as cursor:
        cursor.execute("SELECT COUNT(*) as count FROM clues")
        total_result = cursor.fetchone()
        total_count = total_result["count"] if total_result else 0

        cursor.execute("SELECT status, COUNT(*) as count FROM clues GROUP BY status")
        status_results = cursor.fetchall()

        status_counts = {"pending": 0, "in_progress": 0, "completed": 0}
        for item in status_results:
            if item["status"] in status_counts:
                status_counts[item["status"]] = item["count"]

    return {"code": 200, "data": {"total": total_count, "status_counts": status_counts}}


@router.get("/api/clues/{clue_number}")
def get_clue_detail(clue_number: str, conn=Depends(get_db)):
    """获取线索详情（按线索编号获取所有相关记录）"""
    with conn.cursor(DictCursor) as cursor:
        sql = """
            SELECT
                id, clue_number, title, content_cr_id,
                issue_date, deadline, status,
                responsible_officer, created_at, updated_at
            FROM clues
            WHERE clue_number = %s
            ORDER BY created_at DESC
        """
        cursor.execute(sql, (clue_number,))
        clue_records = cursor.fetchall()

        if not clue_records:
            return {"code": 404, "message": "线索不存在"}

        for clue in clue_records:
            if clue.get("created_at"):
                clue["created_at"] = clue["created_at"].strftime("%Y-%m-%d %H:%M:%S")
            if clue.get("updated_at"):
                clue["updated_at"] = clue["updated_at"].strftime("%Y-%m-%d %H:%M:%S")
            if clue.get("issue_date"):
                clue["issue_date"] = clue["issue_date"].strftime("%Y-%m-%d")
            if clue.get("deadline"):
                clue["deadline"] = clue["deadline"].strftime("%Y-%m-%d")

        temp_ids = []
        for clue in clue_records:
            if clue.get("content_cr_id"):
                temp_ids.append(clue["content_cr_id"].strip())
        temp_ids = list(set(temp_ids))

        captures = []
        if temp_ids:
            placeholders = ", ".join(["%s"] * len(temp_ids))
            capture_sql = f"""
                SELECT
                    id, capture_ids, group_id, camera_index_code,
                    camera_name, start_time, end_time, member_count,
                    members, bkg_urls
                FROM temp_companion_groups
                WHERE id IN ({placeholders})
            """
            cursor.execute(capture_sql, temp_ids)
            captures = cursor.fetchall()

            for capture in captures:
                if capture.get("start_time"):
                    capture["start_time"] = capture["start_time"].strftime("%Y-%m-%d %H:%M:%S")
                if capture.get("end_time"):
                    capture["end_time"] = capture["end_time"].strftime("%Y-%m-%d %H:%M:%S")
                if capture.get("bkg_urls"):
                    capture["bkg_urls"] = capture["bkg_urls"].split(",")
                if capture.get("members"):
                    capture["id_cards"] = capture["members"].split(",")

        result = {
            "clue_number": clue_number,
            "title": clue_records[0]["title"],
            "issue_date": clue_records[0]["issue_date"],
            "deadline": clue_records[0]["deadline"],
            "status": clue_records[0]["status"],
            "responsible_officer": clue_records[0]["responsible_officer"],
            "records": clue_records,
            "captures": captures,
        }

    return {"code": 200, "data": result}


@router.put("/api/clues/{clue_id}")
def update_clue(clue_id: int, body: dict, conn=Depends(get_db)):
    """更新线索"""
    with conn.cursor(DictCursor) as cursor:
        cursor.execute("SELECT id FROM clues WHERE id = %s", (clue_id,))
        if not cursor.fetchone():
            return {"code": 404, "message": "线索不存在"}

        update_fields = []
        params = []

        for field in ("title", "content_cr_id", "issue_date", "deadline", "status", "responsible_officer"):
            if field in body:
                update_fields.append(f"{field} = %s")
                params.append(body[field])

        if update_fields:
            update_fields.append("updated_at = %s")
            params.append(datetime.now())
            params.append(clue_id)

            sql = f"UPDATE clues SET {', '.join(update_fields)} WHERE id = %s"
            cursor.execute(sql, params)
            conn.commit()

    return {"code": 200, "message": "线索更新成功"}


@router.delete("/api/clues/{clue_id}")
def delete_clue(clue_id: int, conn=Depends(get_db)):
    """删除线索"""
    with conn.cursor(DictCursor) as cursor:
        cursor.execute("SELECT id FROM clues WHERE id = %s", (clue_id,))
        if not cursor.fetchone():
            return {"code": 404, "message": "线索不存在"}

        cursor.execute("DELETE FROM clues WHERE id = %s", (clue_id,))
        conn.commit()

    return {"code": 200, "message": "线索删除成功"}
