# -*- coding: utf-8 -*-
"""
任务定义 + 调度器初始化
"""

import logging

from app.config import get_settings
from scheduler.task_scheduler import TaskScheduler

logger = logging.getLogger(__name__)

# 全局调度器实例
scheduler = TaskScheduler()


def _capture_sync_task():
    """抓拍记录同步任务"""
    try:
        from dify_modules.find_all_young_pk_insert_into_db import main as capture_sync_main
        capture_sync_main()
    except Exception as e:
        logger.error(f"抓拍同步任务异常: {e}")
        raise


def _companion_cluster_task():
    """同行人聚类任务"""
    try:
        from dify_modules.choose_peoples_together_insert_into_db import run_companion_clustering
        run_companion_clustering()
    except Exception as e:
        logger.error(f"同行人聚类任务异常: {e}")
        raise


def init_scheduler() -> TaskScheduler:
    """初始化并注册默认任务"""
    settings = get_settings()

    if settings.sync_capture_interval > 0:
        scheduler.register('capture_sync', _capture_sync_task, settings.sync_capture_interval)

    if settings.cluster_interval > 0:
        scheduler.register('companion_cluster', _companion_cluster_task, settings.cluster_interval)

    return scheduler
