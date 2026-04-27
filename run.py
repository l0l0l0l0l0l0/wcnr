# -*- coding: utf-8 -*-
"""
天网系统可视化平台 - 统一启动脚本
使用 uvicorn 启动 FastAPI 服务和后台任务调度器
"""

import logging
import sys

from app.config import get_settings


def setup_logging():
    """配置全局日志"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


if __name__ == "__main__":
    setup_logging()
    settings = get_settings()

    print("=" * 60)
    print("  天网可视化系统启动 (FastAPI)")
    print("=" * 60)
    print(f"  Web 服务: http://{settings.server_host}:{settings.server_port}")
    print(f"  API 文档: http://{settings.server_host}:{settings.server_port}/docs")
    print(f"  调试模式: {'开启' if settings.debug else '关闭'}")
    print(f"  任务调度: {'开启' if settings.scheduler_enabled else '关闭'}")
    print("=" * 60)

    import uvicorn
    uvicorn.run(
        "app.main:create_app",
        factory=True,
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.debug,
    )
