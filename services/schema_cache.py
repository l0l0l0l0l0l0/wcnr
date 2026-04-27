# -*- coding: utf-8 -*-
"""
young_peoples 表列探测缓存
运行时探测表实际有哪些列，应对表结构变更。
"""

from pymysql.cursors import DictCursor
import logging

logger = logging.getLogger(__name__)

_yp_columns_cache = None  # type: set | None


def get_yp_columns(conn) -> set:
    """探测 young_peoples 表实际有哪些列（带缓存）。"""
    global _yp_columns_cache
    if _yp_columns_cache is not None:
        return _yp_columns_cache

    try:
        with conn.cursor(DictCursor) as cursor:
            cursor.execute("SHOW COLUMNS FROM young_peoples")
            _yp_columns_cache = {row["Field"] for row in cursor.fetchall()}
    except Exception:
        _yp_columns_cache = {"id_card_number", "person_face_url", "last_capture_query_time"}

    return _yp_columns_cache
