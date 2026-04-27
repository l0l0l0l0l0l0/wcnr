# -*- coding: utf-8 -*-
"""
兼容层：旧脚本通过 from config import DB_CONFIG 获取数据库配置。
新代码请使用 app.config.get_settings()。
"""

from app.config import get_settings

_settings = get_settings()
DB_CONFIG = _settings.db_config

# 兼容旧名称
DB2_CONFIG = DB_CONFIG

# Flask 兼容配置（供 start.sh 等脚本读取）
FLASK_HOST = _settings.server_host
FLASK_PORT = _settings.server_port
FLASK_DEBUG = _settings.debug

# 海康威视
HIK_APP_KEY = _settings.hik_app_key
HIK_APP_SECRET = _settings.hik_app_secret
HIK_API_BASE_URL = _settings.hik_api_base_url

# 卡口抓拍
CAPTURE_API_URL = _settings.capture_api_url
CAPTURE_BATCH_SIZE = _settings.capture_batch_size
CAPTURE_MAX_RETRIES = _settings.capture_max_retries
CAPTURE_RETRY_DELAY = _settings.capture_retry_delay

# Dify
APP_SECRET = _settings.app_secret

# 调度器
SCHEDULER_ENABLED = _settings.scheduler_enabled
SYNC_CAPTURE_INTERVAL = _settings.sync_capture_interval
CLUSTER_INTERVAL = _settings.cluster_interval
DRIVER_CHECK_INTERVAL = _settings.driver_check_interval
