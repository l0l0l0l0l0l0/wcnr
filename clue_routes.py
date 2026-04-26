# -*- coding: utf-8 -*-
"""
天网系统可视化平台 - 线索管理路由
"""

from app import app
from flask import render_template, jsonify, request
import pymysql
from datetime import datetime
from config import DB_CONFIG


def get_db_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)


@app.route('/clues')
def clues_page():
    """线索展示页面"""
    return render_template('clues.html')


@app.route('/api/clues', methods=['GET'])
def get_clues():
    """获取线索列表（按线索编号分组）"""
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        status = request.args.get('status')
        keyword = request.args.get('keyword', '')

        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # 先获取所有线索编号（去重）
        distinct_sql = """
            SELECT DISTINCT clue_number
            FROM clues
            WHERE 1=1
        """
        params = []

        if status:
            distinct_sql += " AND status = %s"
            params.append(status)

        if keyword:
            distinct_sql += " AND (clue_number LIKE %s OR title LIKE %s OR responsible_officer LIKE %s)"
            params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])

        # 计算总数
        count_sql = "SELECT COUNT(*) as total FROM (" + distinct_sql + ") as count_table"
        cursor.execute(count_sql, params)
        total_result = cursor.fetchone()
        total_count = total_result['total'] if total_result else 0

        # 分页获取线索编号
        distinct_sql += " ORDER BY clue_number DESC LIMIT %s OFFSET %s"
        params.extend([page_size, (page - 1) * page_size])
        cursor.execute(distinct_sql, params)
        clue_numbers = [row['clue_number'] for row in cursor.fetchall()]

        clues = []
        if clue_numbers:
            # 对每个线索编号，获取最新的一条记录
            placeholders = ', '.join(['%s'] * len(clue_numbers))
            sql = f"""
                SELECT
                    id,
                    clue_number,
                    title,
                    content_cr_id,
                    issue_date,
                    deadline,
                    status,
                    responsible_officer,
                    created_at,
                    updated_at
                FROM clues
                WHERE clue_number IN ({placeholders})
                ORDER BY clue_number, created_at DESC
            """
            cursor.execute(sql, clue_numbers)
            all_records = cursor.fetchall()

            # 按线索编号分组，只保留最新的一条
            seen_clue_numbers = set()
            for record in all_records:
                if record['clue_number'] not in seen_clue_numbers:
                    seen_clue_numbers.add(record['clue_number'])
                    if record.get('created_at'):
                        record['created_at'] = record['created_at'].strftime('%Y-%m-%d %H:%M:%S')
                    if record.get('updated_at'):
                        record['updated_at'] = record['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
                    if record.get('issue_date'):
                        record['issue_date'] = record['issue_date'].strftime('%Y-%m-%d')
                    if record.get('deadline'):
                        record['deadline'] = record['deadline'].strftime('%Y-%m-%d')
                    clues.append(record)

        cursor.close()
        conn.close()

        return jsonify({
            'code': 200,
            'data': clues,
            'total': total_count
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})


@app.route('/api/clues', methods=['POST'])
def create_clue():
    """创建线索"""
    try:
        data = request.get_json()

        clue_number = data.get('clue_number')
        title = data.get('title')
        content_cr_id = data.get('content_cr_id')
        issue_date = data.get('issue_date')
        deadline = data.get('deadline')
        status = data.get('status', 'pending')
        responsible_officer = data.get('responsible_officer')

        if not clue_number or not title or not issue_date:
            return jsonify({'code': 400, 'message': '线索编号、标题和下发日期为必填项'})

        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # 移除线索编号唯一性检查，允许一个线索编号对应多条记录

        sql = """
            INSERT INTO clues (clue_number, title, content_cr_id, issue_date, deadline, status, responsible_officer, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        now = datetime.now()
        cursor.execute(sql, (clue_number, title, content_cr_id, issue_date, deadline, status, responsible_officer, now, now))
        conn.commit()

        clue_id = cursor.lastrowid

        cursor.close()
        conn.close()

        return jsonify({
            'code': 200,
            'message': '线索创建成功',
            'data': {'id': clue_id}
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})


@app.route('/api/clues/<string:clue_number>', methods=['GET'])
def get_clue_detail(clue_number):
    """获取线索详情（按线索编号获取所有相关记录）"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # 获取该线索编号下的所有记录
        sql = """
            SELECT
                id,
                clue_number,
                title,
                content_cr_id,
                issue_date,
                deadline,
                status,
                responsible_officer,
                created_at,
                updated_at
            FROM clues
            WHERE clue_number = %s
            ORDER BY created_at DESC
        """
        cursor.execute(sql, (clue_number,))
        clue_records = cursor.fetchall()

        if not clue_records:
            cursor.close()
            conn.close()
            return jsonify({'code': 404, 'message': '线索不存在'})

        # 处理时间格式
        for clue in clue_records:
            if clue.get('created_at'):
                clue['created_at'] = clue['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            if clue.get('updated_at'):
                clue['updated_at'] = clue['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
            if clue.get('issue_date'):
                clue['issue_date'] = clue['issue_date'].strftime('%Y-%m-%d')
            if clue.get('deadline'):
                clue['deadline'] = clue['deadline'].strftime('%Y-%m-%d')

        # 收集所有temp_companion_groups的id
        temp_ids = []
        for clue in clue_records:
            if clue.get('content_cr_id'):
                # content_cr_id存储的是temp_companion_groups的id
                temp_ids.append(clue['content_cr_id'].strip())

        # 去重
        temp_ids = list(set(temp_ids))

        captures = []
        if temp_ids:
            # 使用id字段进行匹配
            placeholders = ', '.join(['%s'] * len(temp_ids))
            capture_sql = f"""
                SELECT
                    id,
                    capture_ids,
                    group_id,
                    camera_index_code,
                    camera_name,
                    start_time,
                    end_time,
                    member_count,
                    members,
                    bkg_urls
                FROM temp_companion_groups
                WHERE id IN ({placeholders})
            """
            cursor.execute(capture_sql, temp_ids)
            captures = cursor.fetchall()

            for capture in captures:
                if capture.get('start_time'):
                    capture['start_time'] = capture['start_time'].strftime('%Y-%m-%d %H:%M:%S')
                if capture.get('end_time'):
                    capture['end_time'] = capture['end_time'].strftime('%Y-%m-%d %H:%M:%S')
                if capture.get('bkg_urls'):
                    capture['bkg_urls'] = capture['bkg_urls'].split(',')
                if capture.get('members'):
                    capture['id_cards'] = capture['members'].split(',')

        # 构建返回数据
        result = {
            'clue_number': clue_number,
            'title': clue_records[0]['title'],  # 使用第一条记录的标题
            'issue_date': clue_records[0]['issue_date'],
            'deadline': clue_records[0]['deadline'],
            'status': clue_records[0]['status'],
            'responsible_officer': clue_records[0]['responsible_officer'],
            'records': clue_records,
            'captures': captures
        }

        cursor.close()
        conn.close()

        return jsonify({
            'code': 200,
            'data': result
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})


@app.route('/api/clues/<int:clue_id>', methods=['PUT'])
def update_clue(clue_id):
    """更新线索"""
    try:
        data = request.get_json()

        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        check_sql = "SELECT id FROM clues WHERE id = %s"
        cursor.execute(check_sql, (clue_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'code': 404, 'message': '线索不存在'})

        update_fields = []
        params = []

        if 'title' in data:
            update_fields.append("title = %s")
            params.append(data['title'])
        if 'content_cr_id' in data:
            update_fields.append("content_cr_id = %s")
            params.append(data['content_cr_id'])
        if 'issue_date' in data:
            update_fields.append("issue_date = %s")
            params.append(data['issue_date'])
        if 'deadline' in data:
            update_fields.append("deadline = %s")
            params.append(data['deadline'])
        if 'status' in data:
            update_fields.append("status = %s")
            params.append(data['status'])
        if 'responsible_officer' in data:
            update_fields.append("responsible_officer = %s")
            params.append(data['responsible_officer'])

        if update_fields:
            update_fields.append("updated_at = %s")
            params.append(datetime.now())
            params.append(clue_id)

            sql = f"UPDATE clues SET {', '.join(update_fields)} WHERE id = %s"
            cursor.execute(sql, params)
            conn.commit()

        cursor.close()
        conn.close()

        return jsonify({
            'code': 200,
            'message': '线索更新成功'
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})


@app.route('/api/clues/<int:clue_id>', methods=['DELETE'])
def delete_clue(clue_id):
    """删除线索"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        check_sql = "SELECT id FROM clues WHERE id = %s"
        cursor.execute(check_sql, (clue_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'code': 404, 'message': '线索不存在'})

        delete_sql = "DELETE FROM clues WHERE id = %s"
        cursor.execute(delete_sql, (clue_id,))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({
            'code': 200,
            'message': '线索删除成功'
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})


@app.route('/api/clues/statistics')
def get_clues_statistics():
    """获取线索统计数据"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        sql_total = "SELECT COUNT(*) as count FROM clues"
        cursor.execute(sql_total)
        total_result = cursor.fetchone()
        total_count = total_result['count'] if total_result else 0

        sql_status = """
            SELECT status, COUNT(*) as count
            FROM clues
            GROUP BY status
        """
        cursor.execute(sql_status)
        status_results = cursor.fetchall()

        status_counts = {
            'pending': 0,
            'in_progress': 0,
            'completed': 0
        }
        for item in status_results:
            if item['status'] in status_counts:
                status_counts[item['status']] = item['count']

        cursor.close()
        conn.close()

        return jsonify({
            'code': 200,
            'data': {
                'total': total_count,
                'status_counts': status_counts
            }
        })
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})
