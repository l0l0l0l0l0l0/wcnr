import pymysql
import requests
import json
import time
import logging
from datetime import datetime, timedelta
from pymysql.cursors import DictCursor
import hashlib
import os
import sys
import base64
from urllib.parse import urlparse

# 添加项目根目录路径以便导入 config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG

# ==================== 配置 ================= ===

# 卡口抓拍接口（注意：请确认你实际使用的 IP 是文档里的 10.33.42.185 还是你之前用的 71.196.11.250）
# 这里暂时保留你原来代码中的 IP，如果报错请切换为文档中的 URL
CAPTURE_API_URL = "http://71.196.11.151:5020/queryDataByImageModelWithPage1"
HEADERS = {
    "Content-Type": "application/json"
}

# 分页设置
BATCH_SIZE = 100

# 重试设置
MAX_RETRIES = 3
RETRY_DELAY = 1

# 字段最大长度
MAX_LEN = {
    'capture_id': 255,
    'camera_name': 255,
    'camera_index_code': 100,
    'gender': 10,
    'age_group': 20,
    'glass': 10,
    'plate_no': 20
}


# ==================== 工具函数 ====================

def is_remote_url(path):
    """判断是否为远端 URL"""
    try:
        result = urlparse(path)
        return all([result.scheme in ('http', 'https'), result.netloc])
    except Exception:
        return False


def is_local_path(path):
    """判断是否为本地文件路径"""
    if is_remote_url(path):
        return False
    if os.path.isabs(path) or path.startswith('./') or path.startswith('/'):
        return True
    if os.path.basename(path):
        return True
    return False


def image_to_base64(image_path):
    """将本地图片转换为 Base64 编码"""
    try:
        image_path = os.path.normpath(image_path)

        if not os.path.exists(image_path):
            logging.error(f"本地图片文件不存在: {image_path}")
            return None

        file_size = os.path.getsize(image_path)
        if file_size > 4 * 1024 * 1024:
            logging.warning(f"图片文件过大 ({file_size / 1024 / 1024:.2f}MB > 4MB)，可能被接口拒绝: {image_path}")

        with open(image_path, 'rb') as f:
            image_data = f.read()

        # 纯 Base64 字符串，无前缀，无换行
        base64_str = base64.b64encode(image_data).decode('utf-8').replace('\n', '').replace('\r', '')

        logging.info(f"成功读取本地图片并转换为 Base64: {image_path} (长度: {len(base64_str)})")
        return base64_str
    except Exception as e:
        logging.error(f"读取本地图片失败: {image_path}, 错误: {e}")
        return None


def format_iso8601_time(dt_str):
    """将 yyyy-MM-dd HH:mm:ss 转换为 ISO8601 格式: yyyy-MM-dd'T'HH:mm:ss.000+08:00"""
    if not dt_str:
        return None
    try:
        # 解析原格式
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        # 格式化为 ISO8601，假设时区为 +08:00
        return dt.strftime("%Y-%m-%dT%H:%M:%S.000+08:00")
    except Exception as e:
        logging.error(f"时间格式转换失败: {dt_str}, 错误: {e}")
        return dt_str


# ==================== 日志配置 ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("capture_records.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)


# ==================== 任务状态管理（保持不变） ====================

class TaskManager:
    def __init__(self, connection):
        self.connection = connection
        self.task_name = "capture_records_sync"
        self.create_task_table()

    def create_task_table(self):
        create_sql = """
        CREATE TABLE IF NOT EXISTS task_status (
            task_name VARCHAR(255) PRIMARY KEY,
            last_run_time DATETIME,
            last_run_hash VARCHAR(64),
            status VARCHAR(50) DEFAULT 'running'
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(create_sql)
                self.connection.commit()
        except Exception as e:
            logging.error(f"创建任务状态表失败: {e}")

    def get_last_run_info(self):
        sql = "SELECT last_run_time, last_run_hash FROM task_status WHERE task_name = %s"
        try:
            with self.connection.cursor(DictCursor) as cursor:
                cursor.execute(sql, (self.task_name,))
                return cursor.fetchone()
        except Exception as e:
            logging.error(f"查询任务状态失败: {e}")
            return None

    def update_task_status(self, run_hash):
        now = datetime.now()
        sql = """
        INSERT INTO task_status (task_name, last_run_time, last_run_hash, status)
        VALUES (%s, %s, %s, 'completed')
        ON DUPLICATE KEY UPDATE
            last_run_time = VALUES(last_run_time),
            last_run_hash = VALUES(last_run_hash),
            status = VALUES(status)
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql, (self.task_name, now, run_hash))
                self.connection.commit()
                logging.info(f"任务状态已更新: {run_hash}")
        except Exception as e:
            logging.error(f"更新任务状态失败: {e}")


# ==================== 动态时间范围 ====================

def get_time_range(days=30):
    now = datetime.now()
    start_time = (now - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    end_time = now.strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"查询时间范围: {start_time} ~ {end_time}")
    return start_time, end_time


START_TIME, END_TIME = get_time_range(days=30)


# ==================== 数据库操作（保持不变） ====================

def get_people_batch(connection, offset=0, limit=BATCH_SIZE):
    sql = """
    SELECT `id_card_number`, `person_face_url`, `last_capture_query_time`
    FROM `young_peoples`
    WHERE `person_face_url` IS NOT NULL
      AND `person_face_url` != ''
      AND `person_face_url` != 'null'
    LIMIT %s OFFSET %s
    """
    try:
        with connection.cursor(DictCursor) as cursor:
            cursor.execute(sql, (limit, offset))
            return cursor.fetchall()
    except Exception as e:
        logging.error(f"查询 young_peoples 表失败: {e}")
        return []


def update_last_query_time(connection, id_card):
    sql = "UPDATE `young_peoples` SET `last_capture_query_time` = NOW() WHERE `id_card_number` = %s"
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, (id_card,))
            connection.commit()
    except Exception as e:
        logging.error(f"更新 last_capture_query_time 失败: {e}")
        connection.rollback()


def format_time_range(last_query_time):
    if not last_query_time:
        return (datetime.now() - timedelta(days=29)).strftime("%Y-%m-%d %H:%M:%S")
    try:
        parsed_time = datetime.strptime(last_query_time, "%Y-%m-%d %H:%M:%S")
        if datetime.now() - parsed_time > timedelta(days=29):
            return (datetime.now() - timedelta(days=29)).strftime("%Y-%m-%d %H:%M:%S")
        else:
            return last_query_time
    except:
        return (datetime.now() - timedelta(days=29)).strftime("%Y-%m-%d %H:%M:%S")


# ==================== 核心修改：查询卡口抓拍数据 ====================

def query_capture_records(face_path, start_time=None):
    """
    查询卡口抓拍数据（增强版：增加严格检验和调试日志）
    """
    # 1. 格式化时间范围为 ISO8601
    formatted_start_str = format_time_range(start_time)
    begin_time_iso = format_iso8601_time(formatted_start_str)
    end_time_iso = format_iso8601_time(END_TIME)

    # 严格校验时间不能为 None
    if not begin_time_iso or not end_time_iso:
        logging.error(f"时间格式化失败，跳过此人. begin={begin_time_iso}, end={end_time_iso}")
        return []

    # 2. 构建 imageInfo 对象
    image_urls_list = []
    image_datas_list = []

    log_prefix = ""

    # 3. 判断图片类型并填入对应字段（严格模式）
    if is_remote_url(face_path):
        image_urls_list.append(face_path)
        log_prefix = "使用远端 URL"
    elif is_local_path(face_path):
        base64_data = image_to_base64(face_path)
        if not base64_data:
            logging.error(f"无法读取本地图片，跳过: {face_path}")
            return []
        # 再次校验 Base64 有效性
        if not isinstance(base64_data, str) or len(base64_data) == 0:
            logging.error(f"Base64 数据无效，跳过: {face_path}")
            return []
        image_datas_list.append(base64_data)
        log_prefix = "使用本地图片 (Base64)"
    else:
        # 兜底：尝试作为 URL
        logging.warning(f"无法识别路径类型，尝试作为 URL 处理: {face_path}")
        image_urls_list.append(face_path)
        log_prefix = "未知路径类型，尝试作为 URL"

    # 4. 构建符合文档标准的 Payload
    payload = {
        "page_number": 1,
        "page_size": 3999,
        "image_urls": image_urls_list,
        "image_datas": image_datas_list,
        "camera_index_code": "",
        "min_similarity": 0.8,
        "max_results": 9999,
        "start_time": begin_time_iso,
        "end_time": end_time_iso,
    }

    # 调试日志：打印关键参数长度，确认不为 None
    logging.info(
        f"{log_prefix}: face_path={face_path[:50]}... | "
        f"Base64Len={len(image_datas_list[0]) if image_datas_list else 0} | "
        f"TimeRange={begin_time_iso} ~ {end_time_iso}"
    )

    for attempt in range(MAX_RETRIES):
        try:
            # 序列化前再次检查
            json_str = json.dumps(payload)
            if len(json_str) > 500000:
                logging.warning(f"请求体过大 ({len(json_str)} bytes)，可能超时")
            response = requests.post(
                CAPTURE_API_URL,
                headers=HEADERS,
                data=json_str,
                timeout=60
            )

            print(f"Status: {response.status_code}")

            # 正确处理编码：先尝试 UTF-8，失败则回退 GBK
            try:
                _ = response.content.decode('utf-8')
                response.encoding = 'utf-8'
            except UnicodeDecodeError:
                response.encoding = 'gbk'

            if response.status_code != 200:
                logging.error(
                    f"HTTP {response.status_code} (尝试 {attempt + 1}/{MAX_RETRIES}): "
                    f"响应: {response.text[:200]}"
                )
                # 如果不是最后一次尝试，进入下一次循环
                if attempt < MAX_RETRIES - 1:
                    sleep_time = RETRY_DELAY * (2 ** attempt)
                    logging.info(f"{sleep_time} 秒后重试...")
                    time.sleep(sleep_time)
                continue

            try:
                result = response.json()
            except json.JSONDecodeError:
                logging.error(f"响应不是合法 JSON: {response.text[:200]}")
                if attempt < MAX_RETRIES - 1:
                    sleep_time = RETRY_DELAY * (2 ** attempt)
                    logging.info(f"{sleep_time} 秒后重试...")
                    time.sleep(sleep_time)
                continue

            # 文档约定成功 code="success" 表示成功
            if result.get("success") and "data" in result:
                records = result["data"].get("records", [])
                logging.info(f"查询成功，共 {len(records)} 条抓拍记录")
                return records
            else:
                msg = result.get("msg", "unknown error")
                code = result.get("code", "unknown")
                logging.error(
                    f"接口返回失败 (尝试 {attempt + 1}/{MAX_RETRIES}): "
                    f"Code={code}, Msg={msg}"
                )

                # 如果是 500 错误，打印详细请求体摘要（不打印完整 Base64 以免刷屏）
                if code == "500" or "Internal server error" in str(msg):
                    debug_payload = payload.copy()
                    if "imageInfo" in debug_payload and "imageDatas" in debug_payload["imageInfo"]:
                        debug_payload["imageInfo"]["imageDatas"] = ["[BASE64_HIDDED]"]
                    logging.error(f"调试信息 - 发送的 Payload: {json.dumps(debug_payload)}")

        except requests.exceptions.Timeout:
            logging.warning(f"请求超时 (尝试 {attempt + 1}/{MAX_RETRIES})")
        except requests.exceptions.ConnectionError as e:
            logging.warning(f"连接错误 (尝试 {attempt + 1}/{MAX_RETRIES}): {e}")
        except Exception as e:
            logging.warning(f"请求异常 (尝试 {attempt + 1}/{MAX_RETRIES}): {e}")

        if attempt < MAX_RETRIES - 1:
            sleep_time = RETRY_DELAY * (2 ** attempt)
            logging.info(f"{sleep_time} 秒后重试...")
            time.sleep(sleep_time)

    logging.error("所有重试均失败，跳过此人")
    return []


# ==================== 数据插入逻辑（需适配返回字段名） ====================

def truncate(text, max_len):
    if not text:
        return None
    return text[:max_len]


def check_existing_capture_ids(connection, capture_ids):
    if not capture_ids:
        return set()
    placeholders = ','.join(['%s'] * len(capture_ids))
    sql = f"SELECT capture_id FROM capture_records WHERE capture_id IN ({placeholders})"
    try:
        with connection.cursor(DictCursor) as cursor:
            cursor.execute(sql, capture_ids)
            result = cursor.fetchall()
            return {row['capture_id'] for row in result if row and 'capture_id' in row}
    except Exception as e:
        logging.error(f"查询已存在 capture_id 失败: {e}")
        return set()


def get_incremental_records(connection, person_id_card, records):
    if not records:
        return []
    capture_ids = [rec.get("id") for rec in records if rec.get("id")]
    existing_ids = check_existing_capture_ids(connection, capture_ids)
    new_records = [rec for rec in records if rec.get("id") not in existing_ids]
    logging.info(
        f"人员 {person_id_card} 共 {len(records)} 条记录，"
        f"其中 {len(new_records)} 条为新增"
    )
    return new_records


def insert_capture_records(connection, person_id_card, person_face_url, records):
    if not records:
        return

    new_records = get_incremental_records(connection, person_id_card, records)

    if not new_records:
        logging.info(f"人员 {person_id_card} 无新增记录")
        return

    insert_sql = """
    INSERT INTO capture_records (
        person_id_card, person_face_url, capture_id, capture_time,
        camera_name, camera_index_code, face_pic_url, bkg_url,
        similarity, gender, age_group, glass, plate_no, is_processed
    ) VALUES (
        %s, %s, %s, %s,
        %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s
    )
    """

    data_list = []
    for rec in new_records:
        capture_time_str = rec.get("captureTime", "")
        capture_time = None
        if capture_time_str:
            try:
                clean_time = capture_time_str.split('.')[0]
                capture_time = datetime.fromisoformat(clean_time)
            except Exception as e:
                logging.warning(f"时间解析失败: {capture_time_str}, {e}")
                pass

        data_list.append((
            person_id_card,
            person_face_url,
            truncate(rec.get("id"), MAX_LEN['capture_id']),
            capture_time,
            truncate(rec.get("cameraName"), MAX_LEN['camera_name']),
            truncate(rec.get("cameraIndexCode"), MAX_LEN['camera_index_code']),
            rec.get("facePicUrl"),
            rec.get("bkgUrl"),
            rec.get("similarity"),
            truncate(rec.get("genderName"), MAX_LEN['gender']),
            truncate(rec.get("ageGroupName"), MAX_LEN['age_group']),
            truncate(rec.get("glassName"), MAX_LEN['glass']),
            truncate(rec.get("plateNo"), MAX_LEN['plate_no']),
            0
        ))

    try:
        with connection.cursor() as cursor:
            cursor.executemany(insert_sql, data_list)
            connection.commit()
            logging.info(f"成功插入 {len(data_list)} 条新抓拍记录")
    except Exception as e:
        logging.error(f"批量插入失败: {e}")
        connection.rollback()


# ==================== 主程序 ====================

def generate_task_hash():
    task_info = f"{START_TIME}_{END_TIME}_{BATCH_SIZE}"
    return hashlib.md5(task_info.encode()).hexdigest()


def main():
    connection = None
    try:
        connection = pymysql.connect(**DB_CONFIG)

        # 初始化任务管理器
        task_manager = TaskManager(connection)

        # 获取上次任务信息
        last_run_info = task_manager.get_last_run_info()
        current_hash = generate_task_hash()

        # 检查是否已执行过相同任务（幂等性）
        if last_run_info and last_run_info.get('last_run_hash') == current_hash:
            logging.info("检测到相同任务已执行，跳过执行（幂等性）")
            return

        logging.info("开始执行抓拍记录同步任务")

        offset = 0
        total_processed = 0
        total_new_records = 0

        while True:
            people = get_people_batch(connection, offset=offset, limit=BATCH_SIZE)
            if not people:
                break

            logging.info(f"当前批次: 从偏移 {offset} 读取 {len(people)} 人")

            for person in people:
                id_card = person['id_card_number'].strip()
                face_url = person['person_face_url'].strip()
                last_query_time = person.get('last_capture_query_time')

                if last_query_time:
                    start_time = last_query_time.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    start_time = None

                logging.info(f"正在查询: {id_card} (从 {start_time or '默认时间'} 开始)")

                records = query_capture_records(face_url, start_time)

                if records:
                    insert_capture_records(connection, id_card, face_url, records)
                    update_last_query_time(connection, id_card)
                else:
                    logging.warning(f"无人脸抓拍记录: {id_card}")

                total_processed += 1

            offset += BATCH_SIZE

        # 更新任务状态
        task_manager.update_task_status(current_hash)

        logging.info(f"全部处理完成，共处理 {total_processed} 人")
        # 注意: total_new_records 变量未在循环中累加，如需统计需在 insert 函数中返回或全局累加

    except Exception as e:
        logging.critical(f"程序异常退出: {e}")
        raise
    finally:
        if connection:
            connection.close()
            logging.info("数据库连接已关闭")


if __name__ == "__main__":
    main()
