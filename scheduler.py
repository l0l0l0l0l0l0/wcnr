# -*- coding: utf-8 -*-
"""
后台任务调度器 - 统一管理数据采集和分析任务
支持定时执行和手动触发
"""

import threading
import time
import logging
import traceback
from datetime import datetime

from config import (
    SCHEDULER_ENABLED,
    SYNC_CAPTURE_INTERVAL,
    CLUSTER_INTERVAL,
    DRIVER_CHECK_INTERVAL,
)

logger = logging.getLogger(__name__)


class TaskScheduler:
    """简易任务调度器，基于 threading.Timer"""

    def __init__(self):
        self._tasks = {}
        self._timers = {}
        self._running = False
        self._lock = threading.Lock()

    def _wrap_task(self, name, func, interval_minutes, *args, **kwargs):
        """包装任务，添加日志和异常处理，并自动重调度"""
        def runner():
            if not self._running:
                return
            start = time.time()
            logger.info(f"[调度器] 任务 '{name}' 开始执行")
            try:
                func(*args, **kwargs)
                elapsed = time.time() - start
                logger.info(f"[调度器] 任务 '{name}' 执行完成，耗时 {elapsed:.1f}s")
            except Exception as e:
                logger.error(f"[调度器] 任务 '{name}' 执行失败: {e}\n{traceback.format_exc()}")

            # 自动重调度
            if self._running and interval_minutes > 0:
                with self._lock:
                    timer = threading.Timer(interval_minutes * 60, runner)
                    timer.daemon = True
                    timer.start()
                    self._timers[name] = timer

        return runner

    def register(self, name, func, interval_minutes=0, *args, **kwargs):
        """
        注册任务
        :param name: 任务名称
        :param func: 任务函数
        :param interval_minutes: 执行间隔（分钟），0表示不自动执行
        """
        self._tasks[name] = {
            'func': func,
            'interval': interval_minutes,
            'args': args,
            'kwargs': kwargs,
        }
        logger.info(f"[调度器] 注册任务 '{name}'，间隔 {interval_minutes} 分钟")

    def start(self):
        """启动调度器"""
        if not SCHEDULER_ENABLED:
            logger.info("[调度器] 调度器已禁用，跳过启动")
            return

        self._running = True
        logger.info("[调度器] 启动调度器")

        for name, task in self._tasks.items():
            interval = task['interval']
            if interval > 0:
                runner = self._wrap_task(
                    name, task['func'], interval,
                    *task['args'], **task['kwargs']
                )
                # 首次延迟10秒后执行，避免与Web服务启动冲突
                timer = threading.Timer(10, runner)
                timer.daemon = True
                timer.start()
                self._timers[name] = timer
                logger.info(f"[调度器] 任务 '{name}' 已启动，每 {interval} 分钟执行一次")

    def stop(self):
        """停止调度器"""
        self._running = False
        with self._lock:
            for name, timer in self._timers.items():
                timer.cancel()
                logger.info(f"[调度器] 任务 '{name}' 已取消")
            self._timers.clear()
        logger.info("[调度器] 调度器已停止")

    def run_now(self, name):
        """立即手动触发某个任务"""
        if name not in self._tasks:
            raise ValueError(f"未知任务: {name}")
        task = self._tasks[name]
        logger.info(f"[调度器] 手动触发任务 '{name}'")
        threading.Thread(
            target=task['func'],
            args=task['args'],
            kwargs=task['kwargs'],
            daemon=True
        ).start()

    def status(self):
        """获取调度器状态"""
        return {
            'running': self._running,
            'tasks': {
                name: {'interval': t['interval']}
                for name, t in self._tasks.items()
            }
        }


# ==================== 任务定义 ====================

def _capture_sync_task():
    """抓拍记录同步任务"""
    try:
        from find_all_young_pk_insert_into_db import main as capture_sync_main
        capture_sync_main()
    except Exception as e:
        logger.error(f"抓拍同步任务异常: {e}")
        raise


def _companion_cluster_task():
    """同行人聚类任务"""
    try:
        from choose_peoples_together_insert_into_db import run_companion_clustering
        run_companion_clustering()
    except Exception as e:
        logger.error(f"同行人聚类任务异常: {e}")
        raise


# 全局调度器实例
scheduler = TaskScheduler()


def init_scheduler():
    """初始化并注册默认任务"""
    if SYNC_CAPTURE_INTERVAL > 0:
        scheduler.register('capture_sync', _capture_sync_task, SYNC_CAPTURE_INTERVAL)

    if CLUSTER_INTERVAL > 0:
        scheduler.register('companion_cluster', _companion_cluster_task, CLUSTER_INTERVAL)

    return scheduler


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    init_scheduler()
    scheduler.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.stop()
