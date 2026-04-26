import pymysql
import logging
import json
from collections import defaultdict, deque
from datetime import timedelta
import threading
from config import DB_CONFIG

# ------------------ 配置 ------------------

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 线程本地存储
_thread_local = threading.local()


def clear_and_insert_tmp_cameras():
    """
    清空tmp_cameras表并插入新的数据
    """
    try:
        # 获取数据库连接
        connection = get_db_connection()

        with connection.cursor() as cursor:
            # 清空tmp_cameras表
            clear_sql = "DELETE FROM tmp_cameras"
            cursor.execute(clear_sql)

            # 插入所有符合条件的摄像头数据
            insert_sql = """
            INSERT INTO tmp_cameras (
                id, cameraIndexCode, gbIndexCode, name, deviceIndexCode,
                longitude, latitude, altitude, pixel, cameraType, cameraTypeName,
                channelNo, capability, subStream, channels, installLocation,
                capabilitiySet, microphoneCapability, intelligentSet, intelligentSetName,
                deviceType, deviceTypeName, deviceCategory, deviceCategoryName,
                deviceCatalog, deviceCatalogName, createTime, updateTime, unitIndexCode, treatyType,
                treatyTypeName, treatyTypeCode, status, statusName
            )
            SELECT
                cr.id, cr.cameraIndexCode, cr.gbIndexCode, cr.name, cr.deviceIndexCode,
                cr.longitude, cr.latitude, cr.altitude, cr.pixel, cr.cameraType, cr.cameraTypeName,
                cr.channelNo, cr.capability, cr.subStream, cr.channels, cr.installLocation,
                cr.capabilitiySet, cr.microphoneCapability, cr.intelligentSet, cr.intelligentSetName,
                cr.deviceType, cr.deviceTypeName, cr.deviceCategory, cr.deviceCategoryName,
                cr.deviceCatalog, cr.deviceCatalogName, cr.createTime, cr.updateTime, cr.unitIndexCode, cr.treatyType,
                cr.treatyTypeName, cr.treatyTypeCode, cr.status, cr.statusName
            FROM tmp_companion_groups tcg
            LEFT JOIN cameras cr ON tcg.camera_index_code = cr.cameraIndexCode
            WHERE cr.cameraIndexCode is not NULL
            GROUP BY cr.cameraIndexCode
            """

            cursor.execute(insert_sql)

            # 提交事务
            connection.commit()

            logger.info("成功清空并插入tmp_cameras表数据")
            return {"status": "success", "message": "tmp_cameras表数据更新完成"}

    except Exception as e:
        logger.error(f"清空并插入tmp_cameras表时发生错误: {e}")
        if 'connection' in locals():
            connection.rollback()
        return {"status": "error", "message": f"数据库操作失败: {str(e)}"}
    finally:
        if 'connection' in locals():
            connection.close()


def get_db_connection():
    """
    获取数据库连接
    """
    if not hasattr(_thread_local, 'connection'):
        _thread_local.connection = pymysql.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            charset='utf8mb4',
            autocommit=False
        )
    return _thread_local.connection


# ------------------ 测试入口 ------------------
if __name__ == "__main__":
    print("正在测试...")
    # response = clear_and_insert_tmp_cameras()
    # print("clear_and_insert_tmp_cameras: ", response)
