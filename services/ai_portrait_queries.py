# -*- coding: utf-8 -*-
"""
AI 画像 —— 人员数据聚合查询
复用 services.db 的连接与查询工具。
"""

import logging
from typing import Any, Dict, List, Optional

from services.db import execute_query

logger = logging.getLogger(__name__)


def get_person_by_id_card(id_card: str) -> Optional[dict]:
    sql = """
        SELECT id, name, gender, contact, id_card_number, address,
               person_category, criminal_record, update_time,
               person_face_url, age, police_station, police_district,
               control_category, control_time, data_source
        FROM young_peoples
        WHERE id_card_number = %s
        LIMIT 1
    """
    return execute_query(sql, (id_card,), fetchone=True)


def get_capture_records_by_person(id_card: str, limit: int = 50) -> List[dict]:
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


def get_cases_by_person(id_card: str) -> List[dict]:
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


def get_population_by_id_card(id_card: str) -> Optional[dict]:
    sql = """
        SELECT name, gender, age, address, contact, promoted, promoted_at
        FROM population_info
        WHERE id_card_number = %s
        LIMIT 1
    """
    return execute_query(sql, (id_card,), fetchone=True)


def get_driver_stats_by_person(id_card: str) -> dict:
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


def get_face_records_by_person(id_card: str, limit: int = 20) -> List[dict]:
    sql = """
        SELECT name, certificateNumber, plateNo, cameraName,
               captureTime, bkgUrl, facePicUrl, genderName, similarity
        FROM face_records
        WHERE certificateNumber = %s
        ORDER BY captureTime DESC
        LIMIT %s
    """
    return execute_query(sql, (id_card, limit))


def aggregate_person_data(id_card: str) -> Dict[str, Any]:
    """聚合指定人员的全量数据，供 AI 分析使用。"""
    person = get_person_by_id_card(id_card)
    if not person:
        raise ValueError(f"未找到身份证号对应的人员: {id_card}")

    return {
        "basic_info": person,
        "capture_records": get_capture_records_by_person(id_card, limit=50),
        "cases": get_cases_by_person(id_card),
        "population_info": get_population_by_id_card(id_card),
        "driver_stats": get_driver_stats_by_person(id_card),
        "face_records": get_face_records_by_person(id_card, limit=20),
    }
