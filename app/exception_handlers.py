# -*- coding: utf-8 -*-
"""
统一异常处理
"""

from fastapi import Request
from fastapi.responses import JSONResponse
import pymysql
import logging

logger = logging.getLogger(__name__)


class DifyModuleUnavailableError(Exception):
    def __init__(self, module_name: str):
        self.module_name = module_name


class AppError(Exception):
    """业务逻辑错误，返回指定 HTTP 状态码和 JSON。"""
    def __init__(self, message: str, status_code: int = 400, success: bool = False):
        self.message = message
        self.status_code = status_code
        self.success = success


def register_handlers(app):
    @app.exception_handler(DifyModuleUnavailableError)
    async def dify_unavailable(request: Request, exc: DifyModuleUnavailableError):
        return JSONResponse(
            status_code=503,
            content={"success": False, "message": f"模块 {exc.module_name} 暂不可用，请检查依赖配置。"},
        )

    @app.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": exc.success, "message": exc.message},
        )

    @app.exception_handler(pymysql.MySQLError)
    async def db_error(request: Request, exc: pymysql.MySQLError):
        logger.error(f"数据库错误: {exc}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"数据库错误: {str(exc)}"},
        )

    @app.exception_handler(Exception)
    async def generic_error(request: Request, exc: Exception):
        logger.error(f"未处理异常: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(exc)},
        )
