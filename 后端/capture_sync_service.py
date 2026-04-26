import pymysql
import requests
import json
import time
import logging
import hashlib
import os
import sys
import base64
from datetime import datetime, timedelta
from pymysql.cursors import DictCursor
from urllib.parse import urlparse

# ==================== 配置 ====================

# 数据库配置（请根据实际环境修改）
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "smart_platform"),
    "charset": "utf8mb4",
    "cursorclass": DictCursor,
}

# 图像抓拍接口配置
# 注意：请确认实际使用的 IP，文档中的 10.33.42.185 或原用的 71.196.11.250
CAPTURE_API_URL = os.getenv(
    "CAPTURE_API_URL", "http://71.196.11.151:5020/queryDataByImageModelWithPage"
)
HEADERS = {"Content-Type": "application/json"}

# 分页设置
BATCH_SIZE = int(os.getenv("BATCH_SIZE", 100))

# 重试设置
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
RETRY_DELAY = int(os.getenv("RETRY_DELAY", 1))

# 字段最大长度
MAX_LEN = {
    "capture_id": 255,
    "camera_name": 255,
    "camera_index_code": 100,
    "gender": 10,
    "age_group": 20,
    "glass": 10,
    "plate_no": 20,
}

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ==================== 工具函数 ====================


def is_remote_url(path: str) -> bool:
    """判断是否为远端 URL"""
    try:
        result = urlparse(path)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False


def truncate_field(value, field_name: str):
    """按配置截断字段值"""
    if value is None:
        return value
    max_len = MAX_LEN.get(field_name)
    if max_len and isinstance(value, str) and len(value) > max_len:
        logger.warning(
            "字段 %s 长度超出限制(%d)，已截断: %s...",
            field_name,
            max_len,
            value[:20],
        )
        return value[:max_len]
    return value


def get_db_connection():
    """获取数据库连接"""
    try:
        conn = pymysql.connect(**DB_CONFIG)
        logger.info("数据库连接成功: %s:%d/%s", DB_CONFIG["host"], DB_CONFIG["port"], DB_CONFIG["database"])
        return conn
    except pymysql.MySQLError as e:
        logger.error("数据库连接失败: %s", e)
        raise


def execute_with_retry(func, *args, **kwargs):
    """带重试机制的执行器"""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return func(*args, **kwargs)
        except (requests.RequestException, pymysql.MySQLError) as e:
            logger.warning("第 %d/%d 次尝试失败: %s", attempt, MAX_RETRIES, e)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)
            else:
                logger.error("达到最大重试次数，操作失败")
                raise


# ==================== API 调用 ====================


def fetch_capture_data(page_no: int = 1, page_size: int = BATCH_SIZE, **filters) -> dict:
    """
    从智能应用平台获取图像抓拍数据

    Args:
        page_no: 页码，从1开始
        page_size: 每页数量
        **filters: 可选过滤条件（如 startTime, endTime, cameraIndexCode 等）

    Returns:
        API 响应字典
    """
    payload = {
        "pageNo": page_no,
        "pageSize": page_size,
    }
    payload.update(filters)

    logger.info("请求图像抓拍数据: page=%d, size=%d, filters=%s", page_no, page_size, filters)

    response = requests.post(
        CAPTURE_API_URL,
        headers=HEADERS,
        data=json.dumps(payload),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


# ==================== 数据处理 ====================


def validate_capture_record(record: dict) -> dict:
    """校验并清洗单条抓拍记录"""
    cleaned = {}

    # 必填字段映射
    field_mapping = {
        "captureId": "capture_id",
        "cameraName": "camera_name",
        "cameraIndexCode": "camera_index_code",
        "gender": "gender",
        "ageGroup": "age_group",
        "glass": "glass",
        "plateNo": "plate_no",
        "captureTime": "capture_time",
        "picUrl": "pic_url",
    }

    for api_field, db_field in field_mapping.items():
        value = record.get(api_field)
        cleaned[db_field] = truncate_field(value, db_field)

    # 时间格式转换
    if cleaned.get("capture_time"):
        try:
            capture_time = cleaned["capture_time"]
            if isinstance(capture_time, (int, float)):
                cleaned["capture_time"] = datetime.fromtimestamp(capture_time / 1000)
            elif isinstance(capture_time, str):
                cleaned["capture_time"] = datetime.strptime(capture_time, "%Y-%m-%d %H:%M:%S")
        except Exception as e:
            logger.warning("capture_time 格式转换失败: %s, 原始值: %s", e, cleaned.get("capture_time"))
            cleaned["capture_time"] = None

    cleaned["created_at"] = datetime.now()
    cleaned["updated_at"] = datetime.now()

    return cleaned


# ==================== 数据库操作 ====================


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS `capture_records` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    `capture_id` VARCHAR(255) NOT NULL COMMENT '抓拍记录ID',
    `camera_name` VARCHAR(255) DEFAULT NULL COMMENT '相机名称',
    `camera_index_code` VARCHAR(100) DEFAULT NULL COMMENT '相机编号',
    `gender` VARCHAR(10) DEFAULT NULL COMMENT '性别',
    `age_group` VARCHAR(20) DEFAULT NULL COMMENT '年龄段',
    `glass` VARCHAR(10) DEFAULT NULL COMMENT '是否戴眼镜',
    `plate_no` VARCHAR(20) DEFAULT NULL COMMENT '车牌号',
    `capture_time` DATETIME DEFAULT NULL COMMENT '抓拍时间',
    `pic_url` VARCHAR(500) DEFAULT NULL COMMENT '图片URL',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY `uk_capture_id` (`capture_id`) USING BTREE,
    KEY `idx_capture_time` (`capture_time`) USING BTREE,
    KEY `idx_camera_code` (`camera_index_code`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='图像抓拍记录表';
"""


def init_table(conn: pymysql.Connection):
    """初始化数据表"""
    with conn.cursor() as cursor:
        cursor.execute(CREATE_TABLE_SQL)
        conn.commit()
        logger.info("数据表初始化完成")


def insert_or_update_records(conn: pymysql.Connection, records: list):
    """批量插入或更新抓拍记录"""
    if not records:
        return 0

    sql = """
    INSERT INTO capture_records (
        capture_id, camera_name, camera_index_code,
        gender, age_group, glass, plate_no,
        capture_time, pic_url, created_at, updated_at
    ) VALUES (
        %(capture_id)s, %(camera_name)s, %(camera_index_code)s,
        %(gender)s, %(age_group)s, %(glass)s, %(plate_no)s,
        %(capture_time)s, %(pic_url)s, %(created_at)s, %(updated_at)s
    )
    ON DUPLICATE KEY UPDATE
        camera_name = VALUES(camera_name),
        camera_index_code = VALUES(camera_index_code),
        gender = VALUES(gender),
        age_group = VALUES(age_group),
        glass = VALUES(glass),
        plate_no = VALUES(plate_no),
        capture_time = VALUES(capture_time),
        pic_url = VALUES(pic_url),
        updated_at = VALUES(updated_at)
    """

    with conn.cursor() as cursor:
        affected = cursor.executemany(sql, records)
        conn.commit()
        return affected


# ==================== 主流程 ====================


def sync_capture_data(start_time=None, end_time=None, camera_index_code=None):
    """
    同步图像抓拍数据主流程

    Args:
        start_time: 开始时间 (datetime)
        end_time: 结束时间 (datetime)
        camera_index_code: 指定相机编号
    """
    conn = get_db_connection()
    try:
        init_table(conn)

        filters = {}
        if start_time:
            filters["startTime"] = start_time.strftime("%Y-%m-%d %H:%M:%S")
        if end_time:
            filters["endTime"] = end_time.strftime("%Y-%m-%d %H:%M:%S")
        if camera_index_code:
            filters["cameraIndexCode"] = camera_index_code

        page_no = 1
        total_synced = 0

        while True:
            resp = execute_with_retry(fetch_capture_data, page_no, BATCH_SIZE, **filters)

            if resp.get("code") != 0:
                logger.error("API 返回错误: %s", resp.get("msg", "未知错误"))
                break

            data = resp.get("data", {})
            records = data.get("list", [])
            total = data.get("total", 0)

            if not records:
                logger.info("第 %d 页无数据，同步结束", page_no)
                break

            # 数据清洗
            cleaned_records = [validate_capture_record(r) for r in records]

            # 入库
            affected = insert_or_update_records(conn, cleaned_records)
            total_synced += affected

            logger.info(
                "第 %d 页同步完成: 本页 %d 条, 成功入库 %d 条, 总计 %d/%d",
                page_no,
                len(records),
                affected,
                total_synced,
                total,
            )

            if len(records) < BATCH_SIZE:
                break

            page_no += 1

        logger.info("同步完成，共入库 %d 条记录", total_synced)

    except Exception as e:
        logger.exception("同步过程发生异常: %s", e)
        raise
    finally:
        conn.close()
        logger.info("数据库连接已关闭")


if __name__ == "__main__":
    # 示例：同步最近24小时的数据
    end_time = datetime.now()
    start_time = end_time - timedelta(days=1)

    logger.info("开始同步图像抓拍数据: %s ~ %s", start_time, end_time)
    sync_capture_data(start_time=start_time, end_time=end_time)
