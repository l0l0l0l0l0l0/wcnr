from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import random
import os
import mimetypes

mimetypes.add_type('font/woff2', '.woff2')
mimetypes.add_type('font/ttf', '.ttf')

app = Flask(__name__, template_folder='.', static_folder='static')
# 基于 app.py 所在目录的绝对路径，确保无论从哪启动都能找到数据库
base_dir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(base_dir, 'instance', 'monitor.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
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


class ControlPerson(db.Model):
    """布控人员表"""
    __tablename__ = 'control_persons'

    id = db.Column(db.Integer, primary_key=True)
    control_id = db.Column(db.String(50), nullable=False, unique=True)  # 布控编号
    name = db.Column(db.String(50), nullable=False)       # 姓名
    id_card = db.Column(db.String(18))                    # 身份证号
    gender = db.Column(db.String(10))                     # 性别
    age = db.Column(db.Integer)                           # 年龄
    ethnicity = db.Column(db.String(20))                  # 民族
    control_library = db.Column(db.String(50))            # 布控库
    control_status = db.Column(db.String(20), default='布控中')  # 布控状态
    latest_alert_time = db.Column(db.DateTime)            # 近24小时最新预警
    sub_bureau = db.Column(db.String(50))                 # 所属分局
    police_station = db.Column(db.String(50))             # 所属派出所
    community = db.Column(db.String(50))                  # 所属社区
    alias = db.Column(db.String(50))                      # 曾用名
    phone = db.Column(db.String(20))                      # 手机号
    household_address = db.Column(db.String(200))         # 户籍地址
    current_address = db.Column(db.String(200))           # 现住址
    photo_url = db.Column(db.String(200))                 # 照片路径
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'control_id': self.control_id,
            'name': self.name,
            'id_card': self.id_card,
            'gender': self.gender,
            'age': self.age,
            'ethnicity': self.ethnicity,
            'control_library': self.control_library,
            'control_status': self.control_status,
            'latest_alert_time': self.latest_alert_time.strftime('%Y-%m-%d %H:%M') if self.latest_alert_time else '--',
            'sub_bureau': self.sub_bureau,
            'police_station': self.police_station,
            'community': self.community,
            'alias': self.alias or '--',
            'phone': self.phone,
            'household_address': self.household_address,
            'current_address': self.current_address,
            'photo_url': self.photo_url,
        }


class ControlRecord(db.Model):
    """布控操作记录表"""
    __tablename__ = 'control_records'

    id = db.Column(db.Integer, primary_key=True)
    control_person_id = db.Column(db.Integer, db.ForeignKey('control_persons.id'))
    action = db.Column(db.String(50), nullable=False)     # 操作类型: 撤控/删除/导入
    operator = db.Column(db.String(50), default='管理员')   # 操作人
    reason = db.Column(db.String(200))                    # 操作原因
    created_at = db.Column(db.DateTime, default=datetime.now)


# ==================== 种子数据 ====================
def init_db():
    with app.app_context():
        db.create_all()

        # 如果已有预警数据则跳过预警数据生成
        has_alert_data = AlertRecord.query.first() is not None
        has_control_data = ControlPerson.query.first() is not None

        if not has_alert_data:
            _seed_alerts()

        if not has_control_data:
            _seed_controls()

        db.session.commit()
        print(f"数据库初始化完成，预警记录: {AlertRecord.query.count()} 条，布控人员: {ControlPerson.query.count()} 条")


def _seed_alerts():
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
        daily_count = random.randint(80, 200)

        for i in range(daily_count):
            time_offset = timedelta(
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
                seconds=random.randint(0, 59)
            )
            alert_time = day_start + time_offset

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


def _seed_controls():
    """生成布控人员种子数据"""
    libraries = ['重点人员库', '在逃人员库', '涉恐人员库']
    statuses = ['布控中', '待审批', '已撤控']
    genders = ['男', '女']
    ethnicities = ['汉族', '壮族', '回族', '瑶族', '苗族']

    # 柳州各分局-派出所-社区 层级数据
    bureau_data = {
        '城中分局': {
            '城中派出所': ['五星社区', '龙城社区', '东门社区'],
            '公园派出所': ['公园社区', '柳侯社区'],
        },
        '鱼峰分局': {
            '箭盘派出所': ['屏山社区', '白云社区'],
            '荣军派出所': ['荣军社区', '岩村社区'],
        },
        '柳南分局': {
            '南站派出所': ['飞鹅社区', '南站社区'],
            '河西派出所': ['河西社区', '宏都社区'],
        },
        '柳北分局': {
            '胜利派出所': ['胜利社区', '北雀社区'],
            '解放派出所': ['解放社区', '雅儒社区'],
        },
        '柳江分局': {
            '拉堡派出所': ['拉堡社区', '荷塘社区'],
            '城东派出所': ['城东社区', '基隆社区'],
        },
    }

    names = [
        ('张伟', '张某'), ('王芳', '芳芳'), ('李娜', '小李'), ('刘洋', '大洋'),
        ('陈静', '静静'), ('杨明', '老杨'), ('赵强', '强子'), ('黄磊', '小磊'),
        ('周杰', '杰哥'), ('吴刚', '刚子'), ('徐丽', '丽丽'), ('孙涛', '涛涛'),
        ('马超', '超哥'), ('朱红', '红红'), ('胡平', '平哥'), ('郭亮', '亮仔'),
        ('林霞', '霞姐'), ('何勇', '勇哥'), ('高明', '明明'), ('罗辉', '辉哥'),
        ('邓敏', '敏敏'), ('萧然', '小萧'), ('唐丽', '唐唐'), ('曾强', '强子'),
        ('彭亮', '亮亮'), ('潘军', '军哥'), ('袁雪', '小雪'), ('蒋文', '文哥'),
        ('蔡华', '华仔'), ('贾敏', '小敏'), ('魏东', '东哥'), ('薛峰', '峰哥'),
        ('叶伟', '伟哥'), ('余洋', '洋洋'), ('杜娟', '娟娟'), ('丁磊', '磊磊'),
        ('夏雨', '小雨'), ('姜波', '波波'), ('范琳', '琳琳'), ('方强', '强哥'),
        ('金辉', '辉仔'), ('谭静', '静静'), ('廖军', '军军'), ('石磊', '石头'),
        ('熊伟', '大熊'), ('孟丽', '小丽'), ('秦波', '波哥'), ('阎敏', '敏姐'),
        ('薛强', '强子'), ('侯勇', '勇子'), ('雷刚', '刚哥'), ('龙飞', '龙哥'),
        ('万敏', '小万'), ('段平', '平子'), ('龚丽', '丽丽'), ('钱伟', '钱哥'),
        ('汤静', '汤汤'), ('孔军', '孔哥'), ('白磊', '小白'), ('洪强', '洪哥'),
    ]

    # 柳州各区地址
    addresses = {
        '城中分局': ['城中区五星街', '城中区解放路', '城中区中山东路', '城中区龙城路', '城中区东环大道'],
        '鱼峰分局': ['鱼峰区屏山大道', '鱼峰区白云路', '鱼峰区荣军路', '鱼峰区箭盘路', '鱼峰区柳石路'],
        '柳南分局': ['柳南区飞鹅路', '柳南区航生路', '柳南区河西西路', '柳南区西环路', '柳南区南站路'],
        '柳北分局': ['柳北区胜利路', '柳北区北雀路', '柳北区解放北路', '柳北区雅儒路', '柳北区跃进路'],
        '柳江分局': ['柳江区拉堡镇兴柳路', '柳江区拉堡镇柳堡路', '柳江区荷塘路', '柳江区基隆路', '柳江区城东大道'],
    }

    now = datetime.now()

    for i, (name, alias) in enumerate(names):
        # 随机选择分局
        sub_bureau = random.choice(list(bureau_data.keys()))
        police_station = random.choice(list(bureau_data[sub_bureau].keys()))
        community = random.choice(bureau_data[sub_bureau][police_station])

        # 状态分布：布控中 60%、待审批 20%、已撤控 20%
        status = random.choices(statuses, weights=[60, 20, 20])[0]

        # 年龄 20~60
        age = random.randint(20, 60)
        birth_year = 2026 - age
        birth_month = random.randint(1, 12)
        birth_day = random.randint(10, 28)

        # 身份证号：4502 + 区码 + 出生日期 + 顺序码 + 校验位（模拟）
        area_code = random.choice(['02', '03', '04', '05', '06'])
        id_card = f"45{area_code}{birth_year}{birth_month:02d}{birth_day:02d}{random.randint(100, 999)}X"

        # 手机号
        phone = f"138{random.randint(1000, 9999)}{random.randint(1000, 9999)}"

        # 地址
        street = random.choice(addresses[sub_bureau])
        house_num = random.randint(1, 200)
        household_address = f"柳州市{street}{house_num}号"
        current_address = f"柳州市{street}{house_num + random.randint(1, 50)}号"

        # 最新预警时间（部分人员有，部分没有）
        latest_alert = None
        if status == '布控中' and random.random() > 0.3:
            latest_alert = now - timedelta(hours=random.randint(1, 24), minutes=random.randint(0, 59))
        elif random.random() > 0.7:
            latest_alert = now - timedelta(hours=random.randint(1, 72), minutes=random.randint(0, 59))

        person = ControlPerson(
            control_id=f"BK{now.strftime('%Y%m%d')}{random.randint(1000, 9999)}",
            name=name,
            id_card=id_card,
            gender=random.choice(genders),
            age=age,
            ethnicity=random.choice(ethnicities),
            control_library=random.choice(libraries),
            control_status=status,
            latest_alert_time=latest_alert,
            sub_bureau=sub_bureau,
            police_station=police_station,
            community=community,
            alias=alias,
            phone=phone,
            household_address=household_address,
            current_address=current_address,
            photo_url=None,
        )
        db.session.add(person)


# ==================== API 路由 ====================

@app.route('/')
def index():
    """首页"""
    return render_template('gov_monitor_v2.html')


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


# ==================== 布控管理 API ====================

@app.route('/api/control/stats')
def get_control_stats():
    """获取布控统计数据"""
    today = datetime.now().date()

    total = ControlPerson.query.count()
    controlling = ControlPerson.query.filter(ControlPerson.control_status == '布控中').count()
    pending = ControlPerson.query.filter(ControlPerson.control_status == '待审批').count()
    revoked = ControlPerson.query.filter(ControlPerson.control_status == '已撤控').count()
    today_new = ControlPerson.query.filter(
        db.func.date(ControlPerson.created_at) == today
    ).count()

    return jsonify({
        'success': True,
        'data': {
            'total': total,
            'controlling': controlling,
            'pending': pending,
            'revoked': revoked,
            'today_new': today_new,
        }
    })


@app.route('/api/controls')
def get_controls():
    """获取布控人员列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    library = request.args.get('library', '')
    status = request.args.get('status', '')
    keyword = request.args.get('keyword', '')
    address = request.args.get('address', '')

    query = ControlPerson.query

    if library:
        query = query.filter(ControlPerson.control_library == library)
    if status:
        query = query.filter(ControlPerson.control_status == status)
    if keyword:
        query = query.filter(
            db.or_(
                ControlPerson.name.contains(keyword),
                ControlPerson.id_card.contains(keyword)
            )
        )
    if address:
        query = query.filter(
            db.or_(
                ControlPerson.household_address.contains(address),
                ControlPerson.current_address.contains(address)
            )
        )

    query = query.order_by(ControlPerson.created_at.desc())
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


@app.route('/api/control/<control_id>')
def get_control_detail(control_id):
    """获取单条布控人员详情"""
    person = ControlPerson.query.filter_by(control_id=control_id).first()
    if not person:
        return jsonify({'success': False, 'message': '记录不存在'}), 404
    return jsonify({'success': True, 'data': person.to_dict()})


@app.route('/api/control/batch_revoke', methods=['POST'])
def batch_revoke_control():
    """批量撤控"""
    data = request.get_json() or {}
    ids = data.get('ids', [])
    reason = data.get('reason', '')

    if not ids:
        return jsonify({'success': False, 'message': '未选择记录'}), 400

    updated = 0
    for control_id in ids:
        person = ControlPerson.query.filter_by(control_id=control_id).first()
        if person and person.control_status != '已撤控':
            person.control_status = '已撤控'
            record = ControlRecord(
                control_person_id=person.id,
                action='撤控',
                reason=reason
            )
            db.session.add(record)
            updated += 1

    db.session.commit()
    return jsonify({'success': True, 'message': f'已成功撤控 {updated} 条记录', 'data': {'updated': updated}})


@app.route('/api/control/batch_delete', methods=['POST'])
def batch_delete_control():
    """批量删除"""
    data = request.get_json() or {}
    ids = data.get('ids', [])

    if not ids:
        return jsonify({'success': False, 'message': '未选择记录'}), 400

    deleted = 0
    for control_id in ids:
        person = ControlPerson.query.filter_by(control_id=control_id).first()
        if person:
            record = ControlRecord(
                control_person_id=person.id,
                action='删除',
                reason='批量删除'
            )
            db.session.add(record)
            db.session.delete(person)
            deleted += 1

    db.session.commit()
    return jsonify({'success': True, 'message': f'已成功删除 {deleted} 条记录', 'data': {'deleted': deleted}})


@app.route('/api/control/import', methods=['POST'])
def import_controls():
    """导入布控人员"""
    data = request.get_json() or {}
    items = data.get('items', [])

    if not items:
        return jsonify({'success': False, 'message': '无数据'}), 400

    imported = 0
    for item in items:
        person = ControlPerson(
            control_id=item.get('control_id') or f"BK{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000,9999)}",
            name=item.get('name', ''),
            id_card=item.get('id_card', ''),
            gender=item.get('gender', ''),
            age=item.get('age'),
            ethnicity=item.get('ethnicity', ''),
            control_library=item.get('control_library', '重点人员库'),
            control_status=item.get('control_status', '布控中'),
            sub_bureau=item.get('sub_bureau', ''),
            police_station=item.get('police_station', ''),
            community=item.get('community', ''),
            alias=item.get('alias', ''),
            phone=item.get('phone', ''),
            household_address=item.get('household_address', ''),
            current_address=item.get('current_address', ''),
        )
        db.session.add(person)
        imported += 1

    db.session.commit()
    return jsonify({'success': True, 'message': f'成功导入 {imported} 条记录', 'data': {'imported': imported}})


@app.route('/api/control/today')
def get_today_controls():
    """今日预警布控人员（近24小时有预警的）"""
    now = datetime.now()
    yesterday = now - timedelta(hours=24)

    persons = ControlPerson.query.filter(
        ControlPerson.latest_alert_time >= yesterday
    ).order_by(ControlPerson.latest_alert_time.desc()).all()

    return jsonify({
        'success': True,
        'data': [p.to_dict() for p in persons]
    })


# ==================== 统计报表 API ====================

@app.route('/api/report/stats')
def get_report_stats():
    """按分局统计报表数据"""
    # 区域到分局的映射
    district_map = {
        '城中区': '城中分局',
        '鱼峰区': '鱼峰分局',
        '柳南区': '柳南分局',
        '柳北区': '柳北分局',
        '柳江区': '柳江分局',
    }

    # 查询所有预警记录
    all_records = AlertRecord.query.all()

    # 按分局聚合统计
    stats = {}
    for record in all_records:
        # 从 location 提取区域
        district = None
        for d in district_map:
            if d in (record.location or ''):
                district = d
                break
        if not district:
            continue

        bureau = district_map[district]
        if bureau not in stats:
            stats[bureau] = {'alerts': 0, 'signed': 0, 'dates': set()}
        stats[bureau]['alerts'] += 1
        if record.status == '已签收':
            stats[bureau]['signed'] += 1
        if record.alert_time:
            stats[bureau]['dates'].add(record.alert_time.date())

    # 构建返回列表
    items = []
    for bureau, data in stats.items():
        total = data['alerts']
        signed = data['signed']
        rate = round(signed / total * 100, 1) if total > 0 else 0
        # 登录人员数模拟：基于不同日期的预警数，取 5%~15%
        staff = max(1, int(len(data['dates']) * random.uniform(0.05, 0.15)))
        items.append({
            'name': bureau,
            'alerts': total,
            'staff': staff,
            'rate': rate,
        })

    # 按预警数量降序排序并添加排名
    items.sort(key=lambda x: x['alerts'], reverse=True)
    for i, item in enumerate(items):
        item['rank'] = i + 1

    # 全局汇总
    total_alerts = sum(item['alerts'] for item in items)
    total_signed = sum(int(item['alerts'] * item['rate'] / 100) for item in items)
    total_rate = round(total_signed / total_alerts * 100, 1) if total_alerts > 0 else 0
    total_staff = sum(item['staff'] for item in items)

    summary = {
        'name': '柳州市公安局',
        'alerts': total_alerts,
        'staff': total_staff,
        'rate': total_rate,
        'rank': 1,
    }

    return jsonify({
        'success': True,
        'data': {
            'summary': summary,
            'items': items,
        }
    })


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5050, debug=True)
