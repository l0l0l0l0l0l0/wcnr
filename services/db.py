# -*- coding: utf-8 -*-
"""
数据库服务层 - 统一连接管理
提供 FastAPI 依赖注入和上下文管理器两种模式。
"""

import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
from typing import Generator
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)


def get_db() -> Generator:
    """FastAPI 依赖：yield pymysql 连接，请求结束后自动关闭。"""
    settings = get_settings()
    conn = pymysql.connect(**settings.db_config)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_db_ctx():
    """上下文管理器：供后台任务和 Dify 脚本使用，自动关闭连接。"""
    settings = get_settings()
    conn = None
    try:
        conn = pymysql.connect(**settings.db_config)
        yield conn
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        raise
    finally:
        if conn:
            conn.close()


@contextmanager
def get_cursor(cursorclass=DictCursor):
    """游标上下文管理器：自动提交/回滚和关闭。"""
    with get_db_ctx() as conn:
        cursor = conn.cursor(cursorclass)
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            cursor.close()


def get_table_columns(conn, table_name: str) -> set:
    """获取表的所有列名。"""
    try:
        with conn.cursor(DictCursor) as cursor:
            cursor.execute(f"SHOW COLUMNS FROM {table_name}")
            return {row["Field"] for row in cursor.fetchall()}
    except Exception as e:
        logger.warning(f"获取表 {table_name} 列信息失败: {e}")
        return set()


def execute_query(sql: str, params=None, fetchone: bool = False):
    """执行查询语句。"""
    with get_cursor() as cursor:
        cursor.execute(sql, params or ())
        return cursor.fetchone() if fetchone else cursor.fetchall()


def execute_update(sql: str, params=None) -> int:
    """执行更新语句，返回影响行数。"""
    with get_cursor() as cursor:
        cursor.execute(sql, params or ())
        return cursor.rowcount
