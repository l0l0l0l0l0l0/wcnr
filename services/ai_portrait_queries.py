# -*- coding: utf-8 -*-
"""
AI 画像 —— 人员数据聚合查询
复用 services.db 的连接与查询工具。
兼容内网数据库：缺失字段/表时跳过，不报错。
"""

import logging
from typing import Any, Dict, List, Optional

from pymysql import err as pymysql_err
from services.db import execute_query, get_table_columns
from services.db import get_db_ctx

logger = logging.getLogger(__name__)


def _table_exists(table_name: str) -> bool:
    try:
        with get_db_ctx() as conn:
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES LIKE %s", (table_name,))
            return cursor.fetchone() is not None
    except Exception:
        return False


def get_person_by_id_card(id_card: str) -> Optional[dict]:
    try:
        with get_db_ctx() as conn:
            cols = get_table_columns(conn, "young_peoples")
            fields = [c for c in [
                "id", "name", "gender", "contact", "id_card_number", "address",
                "person_category", "criminal_record", "update_time",
                "person_face_url", "age", "police_station", "police_district",
                "control_category", "control_time", "data_source",
            ] if c in cols]
            sql = f"SELECT {', '.join(fields)} FROM young_peoples WHERE id_card_number = %s LIMIT 1"
            cursor = conn.cursor()
            cursor.execute(sql, (id_card,))
            return cursor.fetchone()
    except Exception as e:
        logger.warning(f"查询 young_peoples 失败: {e}")
        return None


def get_person_profile_by_id_card(id_card: str) -> Optional[dict]:
    if not _table_exists("person_profiles"):
        return None
    try:
        sql = """
            SELECT id_card_number, birth_date, native_place, household_address,
                   education, school, enrollment_date, graduation_date,
                   subordinate_bureau, person_type_tag,
                   delivery_time, delivery_unit,
                   is_serious_bad_minor, personal_phone, guardian_phone,
                   remarks, bad_behavior_records, racing_behavior, analysis_phone
            FROM person_profiles
            WHERE id_card_number = %s
            LIMIT 1
        """
        return execute_query(sql, (id_card,), fetchone=True)
    except Exception as e:
        logger.warning(f"查询 person_profiles 失败: {e}")
        return None


def get_guardians_by_person(id_card: str) -> List[dict]:
    if not _table_exists("person_guardians"):
        return []
    try:
        sql = """
            SELECT id, guardian_type, name, contact, id_card_number, address, relation
            FROM person_guardians
            WHERE person_id_card = %s
            ORDER BY FIELD(guardian_type, '母亲', '父亲', '其他'), id ASC
        """
        return execute_query(sql, (id_card,))
    except Exception as e:
        logger.warning(f"查询 person_guardians 失败: {e}")
        return []


def get_alert_feedback_by_person(id_card: str, limit: int = 50) -> List[dict]:
    """查询该人员已反馈的历史预警记录（时间、地点、处理内容）。"""
    if not _table_exists("alert_process_logs"):
        return []
    try:
        sql = """
            SELECT cr.capture_time, cr.camera_name, cr.camera_index_code,
                   cr.plate_no, cr.capture_id,
                   apl.feedback_content, apl.handler_name, apl.created_at AS feedback_time
            FROM capture_records cr
            LEFT JOIN alert_process_logs apl ON apl.record_id = cr.id AND apl.action = 'feedback'
            WHERE cr.person_id_card = %s AND cr.is_processed = 2
            ORDER BY cr.capture_time DESC
            LIMIT %s
        """
        rows = execute_query(sql, (id_card, limit))
        result = []
        for r in rows:
            if not r.get("feedback_content"):
                continue
            result.append({
                "time": r.get("capture_time"),
                "location": r.get("camera_name") or "",
                "camera_index_code": r.get("camera_index_code") or "",
                "situation": "未成年人出现在该地点",
                "handling": r.get("feedback_content") or "",
                "handler_name": r.get("handler_name") or "",
                "feedback_time": r.get("feedback_time"),
            })
        return result
    except Exception as e:
        logger.warning(f"查询 alert_feedback 失败: {e}")
        return []


def get_capture_records_by_person(id_card: str, limit: int = 50) -> List[dict]:
    if not _table_exists("capture_records"):
        return []
    try:
        sql = """
            SELECT id, capture_time, camera_name, camera_index_code,
                   face_pic_url, bkg_url, similarity, gender, age_group,
                   glass, plate_no, is_processed, created_at
            FROM capture_records
            WHERE person_id_card = %s
            ORDER BY capture_time DESC
            LIMIT %s
        """
        return execute_query(sql, (id_card, limit))
    except Exception as e:
        logger.warning(f"查询 capture_records 失败: {e}")
        return []


def get_cases_by_person(id_card: str) -> List[dict]:
    if not _table_exists("case_persons") or not _table_exists("cases"):
        return []
    try:
        sql = """
            SELECT c.case_number, c.case_name, c.case_type,
                   c.incident_time, c.incident_location, c.description,
                   cp.role_in_case, cp.person_source
            FROM case_persons cp
            JOIN cases c ON cp.case_id = c.id
            WHERE cp.id_card_number = %s
            ORDER BY c.incident_time DESC
        """
        return execute_query(sql, (id_card,))
    except Exception as e:
        logger.warning(f"查询 cases 失败: {e}")
        return []


def get_population_by_id_card(id_card: str) -> Optional[dict]:
    if not _table_exists("population_info"):
        return None
    try:
        sql = """
            SELECT name, gender, age, address, contact, promoted, promoted_at
            FROM population_info
            WHERE id_card_number = %s
            LIMIT 1
        """
        return execute_query(sql, (id_card,), fetchone=True)
    except Exception as e:
        logger.warning(f"查询 population_info 失败: {e}")
        return None


def get_driver_stats_by_person(id_card: str) -> dict:
    if not _table_exists("driver_status"):
        return {"total_captures": 0, "driver_count": 0, "passenger_count": 0}
    try:
        sql = """
            SELECT
                COUNT(*) AS total_captures,
                SUM(CASE WHEN ds.is_driver = 1 THEN 1 ELSE 0 END) AS driver_count,
                SUM(CASE WHEN ds.is_driver = 0 THEN 1 ELSE 0 END) AS passenger_count
            FROM driver_status ds
            JOIN capture_records cr ON ds.cr_id = cr.id
            WHERE cr.person_id_card = %s
        """
        row = execute_query(sql, (id_card,), fetchone=True)
        if row is None:
            return {"total_captures": 0, "driver_count": 0, "passenger_count": 0}
        return row
    except Exception as e:
        logger.warning(f"查询 driver_status 失败: {e}")
        return {"total_captures": 0, "driver_count": 0, "passenger_count": 0}


def get_face_records_by_person(id_card: str, limit: int = 20) -> List[dict]:
    if not _table_exists("face_records"):
        return []
    try:
        sql = """
            SELECT name, certificateNumber, plateNo, cameraName,
                   captureTime, bkgUrl, facePicUrl, genderName, similarity
            FROM face_records
            WHERE certificateNumber = %s
            ORDER BY captureTime DESC
            LIMIT %s
        """
        return execute_query(sql, (id_card, limit))
    except Exception as e:
        logger.warning(f"查询 face_records 失败: {e}")
        return []


def aggregate_person_data(id_card: str) -> Dict[str, Any]:
    """聚合指定人员的全量数据，供 AI 分析使用。"""
    person = get_person_by_id_card(id_card)
    if not person:
        raise ValueError(f"未找到身份证号对应的人员: {id_card}")

    profile = get_person_profile_by_id_card(id_card) or {}
    # Merge profile fields into basic_info for prompt builder compatibility
    merged = {**person, **{k: v for k, v in profile.items() if v is not None}}

    return {
        "basic_info": merged,
        "guardians": get_guardians_by_person(id_card),
        "alert_feedback": get_alert_feedback_by_person(id_card, limit=50),
        "capture_records": get_capture_records_by_person(id_card, limit=50),
        "cases": get_cases_by_person(id_card),
        "population_info": get_population_by_id_card(id_card),
        "driver_stats": get_driver_stats_by_person(id_card),
        "face_records": get_face_records_by_person(id_card, limit=20),
    }
