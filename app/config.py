# -*- coding: utf-8 -*-
"""
重点人管控系统 - 统一配置 (pydantic-settings)
所有模块从此处读取配置，支持 .env 文件和环境变量覆盖。
"""

from __future__ import annotations

from pydantic_settings import BaseSettings
from pydantic import Field
from pymysql.cursors import DictCursor


class Settings(BaseSettings):
    # ==================== 数据库配置 ====================
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=3306, alias="DB_PORT")
    db_user: str = Field(default="root", alias="DB_USER")
    db_password: str = Field(default="root_password", alias="DB_PASSWORD")
    db_name: str = Field(default="wcnr", alias="DB_NAME")
    db_charset: str = "utf8mb4"

    # ==================== 服务器配置 ====================
    server_host: str = Field(default="0.0.0.0", alias="FLASK_HOST")
    server_port: int = Field(default=8000, alias="FLASK_PORT")
    debug: bool = Field(default=True, alias="FLASK_DEBUG")

    # ==================== 海康威视 API 配置 ====================
    hik_app_key: str = Field(default="", alias="HIK_APP_KEY")
    hik_app_secret: str = Field(default="", alias="HIK_APP_SECRET")
    hik_api_base_url: str = Field(
        default="https://71.196.10.25", alias="HIK_API_BASE_URL"
    )

    # ==================== 卡口抓拍接口配置 ====================
    capture_api_url: str = Field(
        default="http://71.196.11.151:5020/queryDataByImageModelWithPage1",
        alias="CAPTURE_API_URL",
    )
    capture_batch_size: int = Field(default=100, alias="CAPTURE_BATCH_SIZE")
    capture_max_retries: int = Field(default=3, alias="CAPTURE_MAX_RETRIES")
    capture_retry_delay: int = Field(default=1, alias="CAPTURE_RETRY_DELAY")

    # ==================== Dify 服务配置 ====================
    app_secret: str = Field(default="", alias="APP_SECRET_VALUE")

    # ==================== JWT 配置 ====================
    jwt_secret_key: str = Field(default="wcnr-secret-change-in-production", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=480, alias="JWT_EXPIRE_MINUTES")

    # ==================== 任务调度配置 ====================
    scheduler_enabled: bool = Field(default=True, alias="SCHEDULER_ENABLED")
    sync_capture_interval: int = Field(default=30, alias="SYNC_CAPTURE_INTERVAL")
    cluster_interval: int = Field(default=0, alias="CLUSTER_INTERVAL")
    driver_check_interval: int = Field(default=0, alias="DRIVER_CHECK_INTERVAL")

    model_config = {"env_file": ".env", "extra": "ignore", "populate_by_name": True}

    @property
    def db_config(self) -> dict:
        return {
            "host": self.db_host,
            "port": self.db_port,
            "user": self.db_user,
            "password": self.db_password,
            "database": self.db_name,
            "charset": self.db_charset,
            "cursorclass": DictCursor,
        }


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
