# -*- coding: utf-8 -*-
"""
天网系统可视化平台 - 统一启动脚本
同时启动 Flask Web 服务和后台任务调度器
"""

import logging
import threading
import time
import sys

from app import app
from config import FLASK_HOST, FLASK_PORT, FLASK_DEBUG, SCHEDULER_ENABLED
from scheduler import init_scheduler


def setup_logging():
    """配置全局日志"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def start_scheduler():
    """在后台线程启动任务调度器"""
    try:
        scheduler = init_scheduler()
        scheduler.start()
        return scheduler
    except Exception as e:
        logging.getLogger(__name__).error(f"调度器启动失败: {e}")
        return None


if __name__ == '__main__':
    setup_logging()
    logger = logging.getLogger(__name__)

    print("=" * 60)
    print("  天网可视化系统启动")
    print("=" * 60)
    print(f"  Web 服务: http://{FLASK_HOST}:{FLASK_PORT}")
    print(f"  调试模式: {'开启' if FLASK_DEBUG else '关闭'}")
    print(f"  任务调度: {'开启' if SCHEDULER_ENABLED else '关闭'}")
    print("=" * 60)

    # 启动后台任务调度器
    scheduler = None
    if SCHEDULER_ENABLED:
        scheduler = start_scheduler()
        if scheduler:
            print("  后台调度器已启动")
        else:
            print("  后台调度器启动失败")

    # 启动 Flask Web 服务（阻塞主线程）
    try:
        app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG, threaded=True)
    except KeyboardInterrupt:
        print("\n  正在关闭服务...")
        if scheduler:
            scheduler.stop()
        print("  服务已停止")
        sys.exit(0)
