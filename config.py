# -*- coding: utf-8 -*-
"""
重点人管控系统 - 统一配置文件
所有模块从此处读取配置，避免分散和拼写错误。
"""

import os
from pymysql.cursors import DictCursor

# ==================== 数据库配置 ====================
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "root_password"),
    "database": os.getenv("DB_NAME", "wcnr"),
    "charset": "utf8mb4",
    "cursorclass": DictCursor,
}

# 兼容旧名称（部分脚本使用 DB2_CONFIG）
DB2_CONFIG = DB_CONFIG

# ==================== Flask 应用配置 ====================
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "true").lower() in ("1", "true", "yes")

# ==================== 海康威视 API 配置 ====================
HIK_APP_KEY = os.getenv("HIK_APP_KEY", "")
HIK_APP_SECRET = os.getenv("HIK_APP_SECRET", "")
HIK_API_BASE_URL = os.getenv("HIK_API_BASE_URL", "https://71.196.10.25")

# ==================== 卡口抓拍接口配置 ====================
CAPTURE_API_URL = os.getenv(
    "CAPTURE_API_URL",
    "http://71.196.11.151:5020/queryDataByImageModelWithPage1"
)
CAPTURE_BATCH_SIZE = int(os.getenv("CAPTURE_BATCH_SIZE", 100))
CAPTURE_MAX_RETRIES = int(os.getenv("CAPTURE_MAX_RETRIES", 3))
CAPTURE_RETRY_DELAY = int(os.getenv("CAPTURE_RETRY_DELAY", 1))

# ==================== Dify 服务配置 ====================
APP_SECRET = os.getenv("APP_SECRET_VALUE", "")

# ==================== 任务调度配置 ====================
SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "true").lower() in ("1", "true", "yes")
# 各任务的执行间隔（分钟），0 表示不自动执行
SYNC_CAPTURE_INTERVAL = int(os.getenv("SYNC_CAPTURE_INTERVAL", 30))
CLUSTER_INTERVAL = int(os.getenv("CLUSTER_INTERVAL", 0))
DRIVER_CHECK_INTERVAL = int(os.getenv("DRIVER_CHECK_INTERVAL", 0))
