# -*- coding: utf-8 -*-
"""
系统路由 — 健康检查
"""

from fastapi import APIRouter, Depends
from datetime import datetime

from app.dependencies import get_dify_modules

router = APIRouter()


@router.get("/api/health")
def health_check(modules: dict = Depends(get_dify_modules)):
    return {
        "status": "ok",
        "modules": list(modules.keys()),
        "timestamp": datetime.now().isoformat(),
    }
