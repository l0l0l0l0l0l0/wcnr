# -*- coding: utf-8 -*-
"""
Dify 智能分析路由 — 7 个 POST 路由
"""

from fastapi import APIRouter, Depends, Query
import logging

from app.dependencies import get_dify_modules
from app.exception_handlers import DifyModuleUnavailableError

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/queryPersonByAttrWithPage")
def query_person_by_attr(body: dict, modules: dict = Depends(get_dify_modules)):
    """根据人员身份信息查询人脸"""
    if "person_query" not in modules:
        raise DifyModuleUnavailableError("person_query")
    name = body.get("name")
    certificate_number = body.get("certificate_number")
    if not name and not certificate_number:
        return {"error": "name or certificate_number is required"}
    return modules["person_query"](body)


@router.post("/queryByImageModelWithPage")
def query_people_by_images(body: dict, modules: dict = Depends(get_dify_modules)):
    """根据人脸查询身份信息"""
    if "face_compare" not in modules:
        raise DifyModuleUnavailableError("face_compare")
    image_url = body.get("image_url")
    image_data = body.get("image_data")
    model_data = body.get("model_data")
    if not image_url and not image_data and not model_data:
        return {"error": "image_url or image_data or model_data is required"}
    return modules["face_compare"](body)


@router.post("/queryDataByImageModelWithPage1")
def query_allpic_by_url(body: dict, modules: dict = Depends(get_dify_modules)):
    """根据图片URL查询所有抓拍图片和信息"""
    if "allpic_by_url" not in modules:
        raise DifyModuleUnavailableError("allpic_by_url")
    image_urls = body.get("image_urls", [])
    image_datas = body.get("image_datas", [])
    if len(image_urls) == 0 and len(image_datas) == 0:
        return {"error": "image_urls or image_datas is required"}
    return modules["allpic_by_url"](body)


@router.post("/insertFaceRecordsIntoDb")
def insert_face_records(body: dict, certificateNumber: str = Query(...), modules: dict = Depends(get_dify_modules)):
    """将抓拍信息插入或更新到数据库"""
    if "insert_face" not in modules:
        raise DifyModuleUnavailableError("insert_face")
    return modules["insert_face"](body, certificateNumber)


@router.post("/cluster")
def cluster_api(body: dict, modules: dict = Depends(get_dify_modules)):
    """同行人聚类分析"""
    if "cluster" not in modules:
        raise DifyModuleUnavailableError("cluster")
    return modules["cluster"](
        body.get("start_time"),
        body.get("end_time"),
        body.get("time_window_up"),
        body.get("time_window_down"),
        body.get("cameras_type"),
    )


@router.post("/judgeDrivers")
def judge_drivers(body: dict, modules: dict = Depends(get_dify_modules)):
    """判断是否为同机"""
    if "driver" not in modules:
        raise DifyModuleUnavailableError("driver")
    return modules["driver"](body)


@router.post("/updateTmpCameras")
def update_tmp_cameras(modules: dict = Depends(get_dify_modules)):
    """清空并插入tmp_cameras表"""
    if "tmp_cameras" not in modules:
        raise DifyModuleUnavailableError("tmp_cameras")
    return modules["tmp_cameras"]()
