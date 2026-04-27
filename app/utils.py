# -*- coding: utf-8 -*-
"""
通用工具函数
"""


def safe_get(row: dict, key: str, default="--"):
    """安全取值，字段不存在或为空时返回默认值。"""
    if key in row and row[key] is not None:
        val = row[key]
        if isinstance(val, str) and val in ("null", ""):
            return default
        return val
    return default
