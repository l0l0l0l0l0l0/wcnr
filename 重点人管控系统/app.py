from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import random
import os

app = Flask(__name__, template_folder='.', static_folder='.')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///monitor.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_AS_ASCII'] = False

db = SQLAlchemy(app)


# ==================== 数据模型 ====================
class AlertRecord(db.Model):
    """预警记录表"""
    __tablename__ = 'alert_records'

    id = db.Column(db.Integer, primary_key=True)
    alert_id = db.Column(db.String(50), nullable=False)          # 预警编号
    person_name = db.Column(db.String(50), nullable=False)       # 人员姓名
    id_card_tail = db.Column(db.String(10))                      # 身份证号尾号
    similarity = db.Column(db.Float, nullable=False)             # 相似度
    alert_time = db.Column(db.DateTime, nullable=False)          # 预警时间
    location = db.Column(db.String(100))                         # 所在位置
    camera = db.Column(db.String(50))                            # 卡口名称
    alert_type = db.Column(db.String(20))                        # 类型: 人脸/车辆
    status = db.Column(db.String(20), default='待签收')           # 流转状态
    person_tag = db.Column(db.String(50))                        # 人员标签
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.alert_id,
            'name': self.person_name,
            'id_tail': self.id_card_tail,
            'similarity': self.similarity,
            'time': self.alert_time.strftime('%Y-%m-%d %H:%M:%S'),
            'location': self.location,
            'camera': self.camera,
            'type': self.alert_type,
            'status': self.status,
            'person_tag': self.person_tag,
        }


class DailyStat(db.Model):
    """每日统计快照表"""
    __tablename__ = 'daily_stats'

    id = db.Column(db.Integer, primary_key=True)
    stat_date = db.Column(db.Date, nullable=False, unique=True)
    total_alerts = db.Column(db.Integer, default=0)      # 当日预警数
    pending_sign = db.Column(db.Integer, default=0)      # 待签收
    pending_feedback = db.Column(db.Integer, default=0)  # 待反馈
    feedback_done = db.Column(db.Integer, default=0)     # 已反馈
    signed = db.Column(db.Integer, default=0)            # 已签收


# ==================== 种子数据 ====================
def init_db():
    with app.app_context():
        db.create_all()

        # 如果已有数据则跳过
        if AlertRecord.query.first():
            return

        districts = ['城中区', '鱼峰区', '柳南区', '柳北区', '柳江区']
        statuses = ['待签收', '待反馈', '已反馈', '已签收']
        types = ['人脸', '车辆']
        names = ['张伟', '王芳', '李娜', '刘洋', '陈静', '杨明', '赵强', '黄磊',
                 '周杰', '吴刚', '徐丽', '孙涛', '马超', '朱红', '胡平', '郭亮',
                 '林霞', '何勇', '高明', '罗辉']

        now = datetime(2026, 4, 23, 16, 30, 0)

        # 生成历史数据（过去30天）
        for day_offset in range(30, -1, -1):
            day_start = now.replace(hour=0, minute=0, second=0) - timedelta(days=day_offset)
            # 每天随机 80~200 条
            daily_count = random.randint(80, 200)

            for i in range(daily_count):
                time_offset = timedelta(
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                    seconds=random.randint(0, 59)
                )
                alert_time = day_start + time_offset

                # 历史数据大部分已处理
                if day_offset > 3:
                    status = random.choices(
                        ['已签收', '已反馈', '待反馈', '待签收'],
                        weights=[50, 30, 10, 10]
                    )[0]
                else:
                    status = random.choice(statuses)

                record = AlertRecord(
                    alert_id=f"YW{alert_time.strftime('%Y%m%d%H%M%S')}{random.randint(1000,9999)}",
                    person_name=random.choice(names),
                    id_card_tail=f"{random.randint(1000,9999)}",
                    similarity=round(random.uniform(85.0, 99.9), 1),
                    alert_time=alert_time,
                    location=f"柳州市{random.choice(districts)}",
                    camera=f"卡口_{random.randint(1, 20)}",
                    alert_type=random.choice(types),
                    status=status,
                    person_tag='重点人员'
                )
                db.session.add(record)

        # 生成今日统计快照
        today = now.date()
        today_records = AlertRecord.query.filter(
            db.func.date(AlertRecord.alert_time) == today
        ).all()

        stat = DailyStat(
            stat_date=today,
            total_alerts=len(today_records),
            pending_sign=sum(1 for r in today_records if r.status == '待签收'),
            pending_feedback=sum(1 for r in today_records if r.status == '待反馈'),
            feedback_done=sum(1 for r in today_records if r.status == '已反馈'),
            signed=sum(1 for r in today_records if r.status == '已签收'),
        )
        db.session.add(stat)

        db.session.commit()
        print(f"数据库初始化完成，共插入 {AlertRecord.query.count()} 条记录")


# ==================== API 路由 ====================

@app.route('/')
def index():
    """首页"""
    return render_template('gov_monitor.html')


@app.route('/v2')
def index_v2():
    """v2 版本首页"""
    return render_template('gov_monitor_v2.html')


@app.route('/api/stats')
def get_stats():
    """获取统计数据"""
    today = datetime.now().date()

    # 历史预警总数
    total_history = AlertRecord.query.count()

    # 今日预警数
    today_count = AlertRecord.query.filter(
        db.func.date(AlertRecord.alert_time) == today
    ).count()

    # 今日各状态数量
    today_pending_sign = AlertRecord.query.filter(
        db.func.date(AlertRecord.alert_time) == today,
        AlertRecord.status == '待签收'
    ).count()

    today_pending_feedback = AlertRecord.query.filter(
        db.func.date(AlertRecord.alert_time) == today,
        AlertRecord.status == '待反馈'
    ).count()

    today_feedback_done = AlertRecord.query.filter(
        db.func.date(AlertRecord.alert_time) == today,
        AlertRecord.status == '已反馈'
    ).count()

    return jsonify({
        'success': True,
        'data': {
            'history_total': total_history,
            'today_total': today_count,
            'pending_sign': today_pending_sign,
            'pending_feedback': today_pending_feedback,
            'feedback_done': today_feedback_done,
        }
    })


@app.route('/api/alerts')
def get_alerts():
    """获取预警列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status', '')
    alert_type = request.args.get('type', '')
    keyword = request.args.get('keyword', '')

    query = AlertRecord.query

    # 筛选条件
    if status:
        query = query.filter(AlertRecord.status == status)
    if alert_type:
        query = query.filter(AlertRecord.alert_type == alert_type)
    if keyword:
        query = query.filter(
            db.or_(
                AlertRecord.person_name.contains(keyword),
                AlertRecord.alert_id.contains(keyword)
            )
        )

    # 默认按时间倒序
    query = query.order_by(AlertRecord.alert_time.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'success': True,
        'data': {
            'items': [r.to_dict() for r in pagination.items],
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages,
        }
    })


@app.route('/api/alert/<alert_id>')
def get_alert_detail(alert_id):
    """获取单条预警详情"""
    record = AlertRecord.query.filter_by(alert_id=alert_id).first()
    if not record:
        return jsonify({'success': False, 'message': '记录不存在'}), 404
    return jsonify({'success': True, 'data': record.to_dict()})


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5050, debug=True)
