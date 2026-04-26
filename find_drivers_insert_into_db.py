import pymysql
import json
import logging
import re
from datetime import datetime
from config import DB_CONFIG

# ---------------------- 配置 ----------------------

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_driver_status_table():
    """
    创建driver_status表（如果不存在）
    注意：现在表结构已修改，id为自增主键，cr_id为业务ID字段
    """
    connection = None
    try:
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # 创建表的SQL语句 - 注意字段结构已更新
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS driver_status (
            id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            cr_id INT DEFAULT NULL,
            is_driver TINYINT DEFAULT NULL,
            created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY unique_id (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """

        cursor.execute(create_table_sql)
        connection.commit()
        logger.info("driver_status表创建成功或已存在")

    except Exception as e:
        logger.error(f"创建driver_status表时出错: {e}")
        if connection:
            connection.rollback()
        raise
    finally:
        if connection:
            connection.close()


def clean_json_string(json_str):
    """
    清洗JSON字符串，处理包含代码块标记的脏数据

    参数：
        json_str: 可能包含 ```json ``` 标记的字符串

    返回：
        str: 清洗后的JSON字符串
    """
    if not isinstance(json_str, str):
        return json_str

    # 移除代码块标记 ```json 和 ```
    cleaned_str = re.sub(r'^```json\s*', '', json_str.strip(), flags=re.MULTILINE)
    cleaned_str = re.sub(r'```\s*$', '', cleaned_str, flags=re.MULTILINE)

    # 移除多余的空白字符
    cleaned_str = cleaned_str.strip()

    # 验证是否为有效的JSON格式
    try:
        json.loads(cleaned_str)
        return cleaned_str
    except json.JSONDecodeError:
        # 如果清洗后仍然不是有效的JSON，返回原始字符串
        logger.warning(f"清洗后仍不是有效JSON: {json_str}")
        return json_str


def update_driver_status_from_json(json_data):
    """
    根据接收到的JSON数据向driver_status表插入数据，跳过重复cr_id

    参数：
        json_data: 接收到的JSON数据，格式为 {'alldriver': [{'is_driver': 0, 'cr_id': 30402}, {'is_driver': 1, 'cr_id': 30409}]}

    返回：
        dict: 插入结果
    """
    connection = None
    try:
        # 确保表存在
        create_driver_status_table()

        # 连接数据库
        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # 解析JSON数据
        alldriver_list = json_data.get('alldriver', [])

        if not alldriver_list:
            logger.info("没有需要插入的数据")
            return {
                'status': 'success',
                'message': '没有需要插入的数据',
                'updated_count': 0
            }

        print("alldriver_list: ", alldriver_list)
        # 解析每个字符串并插入数据库
        inserted_count = 0
        skipped_count = 0
        for item_str in alldriver_list:
            try:
                # 清洗JSON字符串
                cleaned_item_str = clean_json_string(item_str)

                # 解析JSON字符串
                item = json.loads(cleaned_item_str)

                # 验证必需字段 - 注意现在使用cr_id而不是id
                if 'cr_id' not in item or 'is_driver' not in item:
                    logger.warning(f"跳过无效数据项: {cleaned_item_str}")
                    skipped_count += 1
                    continue

                cr_id_value = item['cr_id']
                is_driver_value = item['is_driver']
                vehicle_type_value = item['vehicle_type']

                # 使用INSERT IGNORE防止重复cr_id插入（基于UNIQUE约束）
                # 注意：现在使用cr_id作为业务ID，id为自增主键
                sql = "INSERT IGNORE INTO driver_status (cr_id, is_driver,vehicle_type) VALUES (%s, %s,%s)"

                try:
                    cursor.execute(sql, (cr_id_value, is_driver_value,vehicle_type_value))
                    if cursor.rowcount > 0:
                        inserted_count += 1
                        logger.info(f"成功插入cr_id为 {cr_id_value} 的记录，is_driver = {is_driver_value}")
                    else:
                        skipped_count += 1
                        logger.info(f"cr_id为 {cr_id_value} 的记录已存在，跳过插入")
                except Exception as e:
                    logger.error(f"插入cr_id为 {cr_id_value} 的记录时出错: {e}")
                    skipped_count += 1
                    continue

            except json.JSONDecodeError as e:
                logger.error(f"JSON解析错误: {e}")
                logger.error(f"原始数据: {item_str}")
                logger.error(f"清洗后数据: {clean_json_string(item_str)}")
                skipped_count += 1
                continue

        # 提交事务
        connection.commit()

        logger.info(f"批量插入完成，共插入 {inserted_count} 条记录，跳过 {skipped_count} 条重复记录")

        return {
            'status': 'success',
            'message': f'成功插入 {inserted_count} 条记录，跳过 {skipped_count} 条重复记录',
            'updated_count': inserted_count
        }

    except Exception as e:
        logger.error(f"数据库插入过程中发生错误: {e}")
        if connection:
            connection.rollback()
        return {
            'status': 'error',
            'message': str(e),
            'updated_count': 0
        }
    finally:
        if connection:
            connection.close()
        logger.info("数据库连接已关闭")


def update_driver_status_by_list(driver_list):
    """
    根据驱动列表直接向driver_status表插入数据，跳过重复cr_id

    参数：
        driver_list: 包含cr_id和is_driver的字典列表
                     格式：[{"cr_id": 30402, "is_driver": 0}, {"cr_id": 30409, "is_driver": 1}]

    返回：
        dict: 插入结果
    """
    connection = None
    try:
        # 确保表存在
        create_driver_status_table()

        connection = pymysql.connect(**DB_CONFIG)
        cursor = connection.cursor()

        if not driver_list:
            logger.info("没有需要插入的数据")
            return {
                'status': 'success',
                'message': '没有需要插入的数据',
                'updated_count': 0
            }

        # 批量插入
        inserted_count = 0
        skipped_count = 0
        for item in driver_list:
            try:
                # 验证必需字段 - 注意现在使用cr_id而不是id
                if 'cr_id' not in item or 'is_driver' not in item:
                    logger.warning(f"跳过无效数据项: {item}")
                    skipped_count += 1
                    continue

                cr_id_value = item['cr_id']
                is_driver_value = item['is_driver']

                # 使用INSERT IGNORE防止重复cr_id插入
                sql = "INSERT IGNORE INTO driver_status (cr_id, is_driver) VALUES (%s, %s)"

                cursor.execute(sql, (cr_id_value, is_driver_value))
                if cursor.rowcount > 0:
                    inserted_count += 1
                    logger.info(f"成功插入cr_id为 {cr_id_value} 的记录，is_driver = {is_driver_value}")
                else:
                    skipped_count += 1
                    logger.info(f"cr_id为 {cr_id_value} 的记录已存在，跳过插入")

            except Exception as e:
                logger.error(f"插入cr_id为 {cr_id_value} 的记录时出错: {e}")
                skipped_count += 1
                continue

        # 提交事务
        connection.commit()

        logger.info(f"批量插入完成，共插入 {inserted_count} 条记录，跳过 {skipped_count} 条重复记录")

        return {
            'status': 'success',
            'message': f'成功插入 {inserted_count} 条记录，跳过 {skipped_count} 条重复记录',
            'updated_count': inserted_count
        }

    except Exception as e:
        logger.error(f"数据库插入过程中发生错误: {e}")
        if connection:
            connection.rollback()
        return {
            'status': 'error',
            'message': str(e),
            'updated_count': 0
        }
    finally:
        if connection:
            connection.close()
        logger.info("数据库连接已关闭")


# 测试函数
def test_update_function():
    """测试更新函数"""
    # 测试数据 - 包含脏数据格式
    test_data = {
        'alldriver': [
            '{"is_driver": 0, "cr_id": 30402}',
            '{"is_driver": 1, "cr_id": 30409}',
            '```json\n{\n  "is_driver": 1,\n  "cr_id": 62633\n}\n```'
        ]
    }

    result = update_driver_status_from_json(test_data)
    print("测试结果:", result)


# 新增的测试函数来测试清洗功能
def test_clean_function():
    """测试清洗函数"""
    test_cases = [
        '{"is_driver": 0, "cr_id": 30402}',
        '```json\n{\n  "is_driver": 1,\n  "cr_id": 62633\n}\n```',
        '```json\n{"is_driver": 1, "cr_id": 62634}\n```',
        'invalid json string',
        '```json\n{\n  "is_driver": 1,\n  "cr_id": 62635\n}\n```'
    ]

    print("=== 测试清洗函数 ===")
    for i, test_case in enumerate(test_cases):
        cleaned = clean_json_string(test_case)
        print(f"测试 {i + 1}:")
        print(f"  原始: {test_case}")
        print(f"  清洗后: {cleaned}")
        print()


if __name__ == "__main__":
    # 运行测试
    test_update_function()
    print("\n" + "=" * 50 + "\n")
    test_clean_function()
