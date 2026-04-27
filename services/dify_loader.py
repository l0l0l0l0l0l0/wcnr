# -*- coding: utf-8 -*-
"""
Dify 模块动态加载
尝试导入可选的 Dify 分析模块，缺失时对应模块不可用。
"""

import logging

logger = logging.getLogger(__name__)

_modules = None  # type: dict | None


def load_dify_modules() -> dict:
    global _modules
    if _modules is not None:
        return _modules

    _modules = {}

    try:
        from dify_modules.queryPersonByAttrWithPage import dify_call_person_query
        _modules["person_query"] = dify_call_person_query
    except Exception as e:
        logger.warning(f"[Dify] 人员身份查询模块未加载: {e}")

    try:
        from dify_modules.queryByImageModelWithPage import dify_call_face_compare
        _modules["face_compare"] = dify_call_face_compare
    except Exception as e:
        logger.warning(f"[Dify] 人脸比对模块未加载: {e}")

    try:
        from dify_modules.queryDataByImageModelWithPage1 import dify_call_allpic_by_url
        _modules["allpic_by_url"] = dify_call_allpic_by_url
    except Exception as e:
        logger.warning(f"[Dify] 图片URL查询模块未加载: {e}")

    try:
        from dify_modules.insert_face_records import difly_call_insert_face_records as dify_call_insert_face_records
        _modules["insert_face"] = dify_call_insert_face_records
    except Exception as e:
        logger.warning(f"[Dify] 抓拍入库模块未加载: {e}")

    try:
        from dify_modules.choose_peoples_together_insert_into_db import run_companion_clustering
        _modules["cluster"] = run_companion_clustering
    except Exception as e:
        logger.warning(f"[Dify] 同行人聚类模块未加载: {e}")

    try:
        from dify_modules.find_drivers_insert_into_db import update_driver_status_from_json
        _modules["driver"] = update_driver_status_from_json
    except Exception as e:
        logger.warning(f"[Dify] 同机判断模块未加载: {e}")

    try:
        from dify_modules.operate_jddb_by_http import clear_and_insert_tmp_cameras
        _modules["tmp_cameras"] = clear_and_insert_tmp_cameras
    except Exception as e:
        logger.warning(f"[Dify] 摄像头同步模块未加载: {e}")

    return _modules
