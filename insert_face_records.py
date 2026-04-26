import json
import pymysql
from datetime import datetime
from config import DB_CONFIG


def difly_call_insert_face_records(body_str, certificate_number):
    """
    将 face_records 插入数据库，并将所有记录的 certificateNumber 替换为传入的值
    :param body_str: 原始响应的 body 字符串 (JSON 格式)
    :param certificate_number: 从 URL 参数传入的身份证号，用于覆盖所有记录
    """
    # 数据库连接
    connection = pymysql.connect(**DB_CONFIG)

    try:
        records = body_str['data']['records']

        with connection.cursor() as cursor:
            insert_sql = """
            INSERT INTO face_records (
                id, name, certificateNumber, plateNo, cameraName,
                cameraIndexCode, captureTime, bkgUrl, facePicUrl,
                genderName, similarity
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s
            ) ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                certificateNumber = VALUES(certificateNumber),  -- 也会被更新为传入值
                plateNo = VALUES(plateNo),
                cameraName = VALUES(cameraName),
                cameraIndexCode = VALUES(cameraIndexCode),
                captureTime = VALUES(captureTime),
                bkgUrl = VALUES(bkgUrl),
                facePicUrl = VALUES(facePicUrl),
                genderName = VALUES(genderName),
                similarity = VALUES(similarity)
            """

        def clean_value(val):
            if val in (None, 'unknown', 'null', '', 'Unknown'):
                return None
            return val

        for record in records:
            # 处理时间
            capture_time_str = record.get('captureTime')
            capture_time = None
            if capture_time_str:
                try:
                    capture_time = datetime.fromisoformat(capture_time_str.replace("+08:00", ""))
                except ValueError as e:
                    print(f"时间解析失败: {capture_time_str}, 错误: {e}")
                    capture_time = None

            # 构造数据行: certificateNumber 使用传入的值
            row = (
                clean_value(record.get('id')),
                clean_value(record.get('name')),
                certificate_number,  # 强制替换为传入的 certificate_number
                clean_value(record.get('plateNo')),
                clean_value(record.get('cameraName')),
                clean_value(record.get('cameraIndexCode')),
                capture_time,
                clean_value(record.get('bkgUrl')),
                clean_value(record.get('facePicUrl')),
                clean_value(record.get('genderName')),
                float(record.get('similarity')) if record.get('similarity') not in (None, 'unknown', 'Unknown', '') else None
            )

            cursor.execute(insert_sql, row)

        connection.commit()
        print(f"成功插入或更新 {len(records)} 条记录，所有记录的 certificateNumber 已替换为: {certificate_number}")

    except Exception as e:
        print("发生错误:", str(e))
        connection.rollback()
        raise

    finally:
        connection.close()
