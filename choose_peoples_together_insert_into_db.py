import pymysql
import json
import logging
from datetime import datetime
from collections import defaultdict, deque
from datetime import timedelta
import threading
from config import DB_CONFIG

# ======================== 配置 ========================

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# -------------------- 线程本地存储 --------------------
_thread_local = threading.local()

# -------------------- 获取时间范围（默认近一个月） --------------------
def get_time_range(start_time_str=None, end_time_str=None):
    """获取时间范围，默认为近一个月"""
    try:
        if start_time_str and end_time_str:
            start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
            end_time = datetime.strptime(end_time_str, '%Y-%m-%d %H:%M:%S')
        else:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=30)

        start_time_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
        end_time_str = end_time.strftime('%Y-%m-%d %H:%M:%S')

        start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
        end_time = datetime.strptime(end_time_str, '%Y-%m-%d %H:%M:%S')

        return start_time, end_time
    except ValueError as e:
        logger.error(f'时间格式错误：{e}')
        raise

# -------------------- 获取时间窗口（默认0-3600秒） --------------------
def get_time_window(time_window_up=None, time_window_down=None):
    """获取时间窗口，默认为0-3600秒"""
    try:
        if time_window_up is None:
            time_window_up = 600
        if time_window_down is None:
            time_window_down = 0
        return time_window_up, time_window_down
    except ValueError as e:
        logger.error(f'时间窗口输入错误：{e}')
        raise

# -------------------- 从数据库读取指定时间范围内的抓拍记录 --------------------
def load_capture_data_by_time_range(connection, start_time, end_time, type_name):
    sql = """
    SELECT
        cr.id,
        cr.person_id_card,
        cr.camera_index_code,
        cr.capture_time,
        cr.bkg_url,
        cr.camera_name
    FROM capture_records cr LEFT JOIN cameras_type ct ON cr.camera_name = ct.camera_name
    WHERE
        capture_time >= %s
        AND capture_time <= %s
        AND bkg_url IS NOT NULL
        AND bkg_url != ''
        AND ct.type_name = %s
    ORDER BY camera_index_code, capture_time
    """
    cursor = connection.cursor()
    cursor.execute(sql, (start_time, end_time, type_name))
    results = cursor.fetchall()
    cursor.close()
    records = []
    for row in results:
        records.append({
            'id': row[0],
            'person_id_card': row[1].strip(),
            'camera_index_code': row[2].strip(),
            'capture_time': row[3],
            'bkg_url': row[4].strip(),
            'camera_name': row[5].strip() if row[5] else ''
        })
    logger.info(f'加载 {len(records)} 条抓拍记录（时间范围：{start_time} 到 {end_time}）')
    return records

# -------------------- 创建临时表 --------------------
def create_temp_table(connection):
    """创建临时表（支持多线程）"""
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS temp_companion_groups (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        group_id VARCHAR(100) NOT NULL,
        camera_index_code VARCHAR(100),
        camera_name VARCHAR(255),
        start_time DATETIME,
        end_time DATETIME,
        member_count INT,
        members TEXT NOT NULL,
        bkg_urls TEXT NOT NULL,
        capture_ids TEXT NOT NULL,
        time_window_diff INT,
        batch_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_group_id (group_id),
        INDEX idx_camera (camera_index_code),
        INDEX idx_time (start_time),
        INDEX idx_batch_time (batch_time),
        INDEX idx_member_count (member_count),
        INDEX idx_capture_ids (capture_ids(255))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """

    cursor = connection.cursor()
    cursor.execute(create_table_sql)
    connection.commit()
    cursor.close()
    logger.info("临时表 temp_companion_groups 已创建")

# -------------------- 连通性聚类：基于连通分量（时间差在指定范围内） --------------------
def cluster_companions_connected(records, time_window_up, time_window_down):
    if not records:
        return []
    all_groups = []
    group_id_counter = 0
    camera_to_records = defaultdict(list)
    for rec in records:
        camera_to_records[rec['camera_index_code']].append(rec)

    for camera_code, group in camera_to_records.items():
        if len(group) < 2:
            continue
        group = sorted(group, key=lambda x: x['capture_time'])
        n = len(group)

        graph = defaultdict(set)
        left = 0
        for right in range(n):
            while (group[right]['capture_time'] - group[left]['capture_time']).total_seconds() > time_window_up:
                left += 1
            for k in range(left, right):
                time_diff = (group[right]['capture_time'] - group[k]['capture_time']).total_seconds()
                if time_window_down <= time_diff <= time_window_up:
                    id_k = group[k]['person_id_card']
                    id_r = group[right]['person_id_card']
                    if id_k != id_r:
                        graph[id_k].add(id_r)
                        graph[id_r].add(id_k)

            if not graph:
                continue

            visited = set()
            for person in list(graph.keys()):
                if person not in visited:
                    queue = deque([person])
                    component = set()
                    urls = {}
                    capture_ids = {}
                    camera_name = None
                    visited.add(person)
                    component.add(person)
                    for rec in group:
                        if rec['person_id_card'] == person:
                            urls[person] = rec['bkg_url']
                            capture_ids[person] = rec['id']
                            camera_name = rec['camera_name']
                            break

                    while queue:
                        node = queue.popleft()
                        for neighbor in graph[node]:
                            if neighbor not in visited:
                                visited.add(neighbor)
                                component.add(neighbor)
                                for rec in group:
                                    if rec['person_id_card'] == neighbor:
                                        urls[neighbor] = rec['bkg_url']
                                        capture_ids[neighbor] = rec['id']
                                        camera_name = rec['camera_name']
                                        break
                                queue.append(neighbor)

            if len(component) < 2:
                continue

            group_records = []
            for rec in group:
                if rec['person_id_card'] in component:
                    group_records.append(rec)
            group_records.sort(key=lambda x: x['capture_time'])

            is_continuous = True
            for i in range(1, len(group_records)):
                time_diff = (
                    group_records[i]['capture_time'] - group_records[i - 1]['capture_time']
                ).total_seconds()
                if time_diff > time_window_up:
                    is_continuous = False
                    break

            if not is_continuous:
                continue

            start_time = group_records[0]['capture_time']
            end_time = group_records[-1]['capture_time']
            member_ids = sorted(component)

            # 直接按逗号格式化学符串
            members_str = ",".join(member_ids)  # person_id_card1,person_id_card2,...
            bkg_urls_str = ",".join([urls[pid] for pid in member_ids])  # bkg_url1,bkg_url2,...
            capture_ids_str = ",".join([str(capture_ids[pid]) for pid in member_ids])  # id1,id2,id3,...

            group_id = f"{camera_code}_{start_time.strftime('%Y%m%d%H%M%S')}_{group_id_counter}"
            time_window_diff = time_window_up - time_window_down

            all_groups.append({
                'group_id': group_id,
                'camera_index_code': camera_code,
                'camera_name': camera_name,
                'start_time': start_time,
                'end_time': end_time,
                'member_count': len(component),
                'members': members_str,  # 修改后的格式
                'bkg_urls': bkg_urls_str,  # 修改后的格式
                'capture_ids': capture_ids_str,  # 修改后的格式
                'time_window_diff': time_window_diff
            })
            group_id_counter += 1

    logger.info(f"聚类完成，共发现 {len(all_groups)} 个同行组（时间窗口：{time_window_down}s - {time_window_up}s）")
    return all_groups

# -------------------- 保存结果到临时表 --------------------
def save_to_temp_table(connection, groups):
    """保存结果到临时表，已存在的只要更新time_window_diff"""
    # 先检查capture_ids是否存在
    check_sql = "SELECT id FROM temp_companion_groups WHERE capture_ids = %s"
    update_sql = """
    UPDATE temp_companion_groups
    SET time_window_diff = %s, batch_time = %s
    WHERE capture_ids = %s
    """
    insert_sql = """
    INSERT INTO temp_companion_groups
    (group_id, camera_index_code, camera_name, start_time, end_time, member_count, members, bkg_urls, capture_ids, time_window_diff, batch_time)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    batch_time = datetime.now()
    insert_data = []
    update_count = 0
    insert_count = 0

    cursor = connection.cursor()

    # 修改为：检查capture_ids是否存在且time_window_diff不同时才更新
    check_with_time_sql = "SELECT id, time_window_diff FROM temp_companion_groups WHERE capture_ids = %s"

    for g in groups:
        # 检查capture_ids是否存在及当前time_window_diff值
        cursor.execute(check_with_time_sql, (g['capture_ids'],))
        existing = cursor.fetchone()

        if existing:
            # 只有当time_window_diff不同时才更新
            if existing[1] != g['time_window_diff']:
                cursor.execute(update_sql, (g['time_window_diff'], batch_time, g['capture_ids']))
                update_count += 1
        else:
            # 插入新记录
            insert_data.append((
                g['group_id'],
                g['camera_index_code'],
                g['camera_name'],
                g['start_time'],
                g['end_time'],
                g['member_count'],
                g['members'],
                g['bkg_urls'],
                g['capture_ids'],
                g['time_window_diff'],
                batch_time
            ))

    # 批量插入新记录
    if insert_data:
        cursor.executemany(insert_sql, insert_data)
        insert_count = len(insert_data)

    connection.commit()
    cursor.close()
    logger.info(f"成功更新 {update_count} 个同行组，插入 {insert_count} 个新同行组到临时表 temp_companion_groups")

# ======================== API接口函数 ========================
def run_companion_clustering(start_time=None, end_time=None, time_window_up=None, time_window_down=None, cameras_type=None):
    """供IoT平台调用的API接口函数【支持多线程】"""
    """
    参数：
        start_time: 开始时间字符串（格式：'YYYY-MM-DD HH:MM:SS'）
        end_time: 结束时间字符串（格式：'YYYY-MM-DD HH:MM:SS'）
        time_window_up: 时间窗口上限（秒）
        time_window_down: 时间窗口下限（秒）
    返回：聚类结果和统计信息
    """
    connection = None
    result = {}
    try:
        connection = pymysql.connect(**DB_CONFIG)
        logger.info("开始【时间范围 + 临时表】同行人聚类任务...")

        # 获取时间范围
        start_time, end_time = get_time_range(start_time, end_time)

        # 获取时间窗口
        time_window_up, time_window_down = get_time_window(time_window_up, time_window_down)

        # 创建临时表
        create_temp_table(connection)

        # 读取指定时间范围内的数据
        records = load_capture_data_by_time_range(connection, start_time, end_time, cameras_type)

        if not records:
            logger.info("无抓拍数据，任务结束")
            result['status'] = 'success'
            result['message'] = '无抓拍数据'
            result['data'] = {
                'records_count': 0,
                'groups_count': 0,
                'groups': []
            }
            return result

        # 执行聚类
        groups = cluster_companions_connected(records, time_window_up, time_window_down)

        if not groups:
            logger.info("无同行组")
            result['status'] = 'success'
            result['message'] = '无同行组'
            result['data'] = {
                'records_count': len(records),
                'groups_count': 0,
                'groups': []
            }
        else:
            # 保存到临时表
            save_to_temp_table(connection, groups)

            # 构造返回数据
            result['status'] = 'success'
            result['message'] = '聚类完成'
            result['data'] = {
                'records_count': len(records),
                'groups_count': len(groups),
                'groups': groups
            }

            # 添加统计信息
            person_count = defaultdict(int)
            for g in groups:
                # 由于members是逗号分隔的字符串，需要先分割
                member_ids = g['members'].split(',') if g['members'] else []
                for pid in member_ids:
                    person_count[pid] += 1
                top_companions = sorted(person_count.items(), key=lambda x: -x[1])[:10]
                result['data']['top_companions'] = top_companions

    except Exception as e:
        logger.critical(f"程序异常：{e}", exc_info=True)
        result['status'] = 'error'
        result['message'] = str(e)
        result['data'] = {}
    finally:
        if connection:
            connection.close()
        logger.info("同行聚类任务结束")
    return result

# -------------------- 测试入口 --------------------
if __name__ == "__main__":
    print("正在使用本地图片测试...")
    result = run_companion_clustering("2026-03-02 17:04:37", "2026-03-03 17:04:37", 30, None, '白名单')
