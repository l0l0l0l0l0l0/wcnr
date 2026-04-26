# -*- coding: utf-8 -*-
"""
数据库服务层 - 统一连接管理和常用查询
"""

import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
import logging

from config import DB_CONFIG

logger = logging.getLogger(__name__)


@contextmanager
def get_db():
    """获取数据库连接上下文管理器，自动关闭"""
    conn = None
    try:
        conn = pymysql.connect(**DB_CONFIG)
        yield conn
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        raise
    finally:
        if conn:
            conn.close()


@contextmanager
def get_cursor(cursorclass=DictCursor):
    """获取游标上下文管理器，自动提交/回滚和关闭"""
    with get_db() as conn:
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


def get_table_columns(conn, table_name):
    """获取表的所有列名"""
    try:
        with conn.cursor(DictCursor) as cursor:
            cursor.execute("SHOW COLUMNS FROM %s", (table_name,))
            return {row['Field'] for row in cursor.fetchall()}
    except Exception as e:
        logger.warning(f"获取表 {table_name} 列信息失败: {e}")
        return set()


def execute_query(sql, params=None, fetchone=False):
    """执行查询语句"""
    with get_cursor() as cursor:
        cursor.execute(sql, params or ())
        return cursor.fetchone() if fetchone else cursor.fetchall()


def execute_update(sql, params=None):
    """执行更新语句，返回影响行数"""
    with get_cursor() as cursor:
        cursor.execute(sql, params or ())
        return cursor.rowcount
