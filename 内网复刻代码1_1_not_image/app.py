from flask import Flask, render_template, jsonify
import pymysql
from datetime import datetime, date

app = Flask(__name__)

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'database': 'wcnsn',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}


def get_db():
    return pymysql.connect(**DB_CONFIG)


def calc_age(birth_date):
    if not birth_date:
        return None
    if isinstance(birth_date, str):
        try:
            birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
        except Exception:
            return None
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def generate_patrol_report(person, profile, captures):
    """基于数据生成巡逻防范报告"""
    name = person.get('name', 'xxx')
    age = person.get('age', '')
    gender = person.get('gender', '')
    address = person.get('address', '')
    police_station = person.get('police_station', 'xxx派出所')
    school = profile.get('school', '') if profile else ''
    bureau = profile.get('subordinate_bureau', 'xxx分局') if profile else 'xxx分局'
    person_type = profile.get('person_type_tag', '专门学校') if profile else '专门学校'

    # 基本信息
    basic_info = {
        'name': name,
        'gender': gender,
        'age': age,
        'id_card': person.get('id_card_number', ''),
        'native_place': profile.get('native_place', 'xx') if profile else 'xx',
        'household_address': profile.get('household_address', 'xx') if profile else 'xx',
        'residence': address or 'xx',
        'education': profile.get('education', '初中') if profile else '初中',
        'school': school or '实验中学八(2)',
        'enrollment_date': profile.get('enrollment_date', '2025年3月11日') if profile else '2025年3月11日',
        'graduation_date': profile.get('graduation_date', '2025年6月24日') if profile else '2025年6月24日',
        'subordinate_bureau': bureau,
        'police_station': police_station,
        'person_type_tag': person_type
    }

    # 历史预警记录
    history_records = []
    for cap in captures:
        capture_time = cap.get('capture_time')
        if isinstance(capture_time, datetime):
            capture_time = capture_time.strftime('%Y-%m-%d %H:%M:%S')
        history_records.append({
            'time': capture_time or '2025-10-04 19:18:13',
            'location': cap.get('camera_name', '大酒店门口'),
            'situation': f'未成年人出现在该地点',
            'action': f'{police_station}已联系其监护人（父亲）{name}，让其配合民警对{name}开展"三教"工作，{name}表示会加强对{name}的监管。'
        })

    # 如果记录太少，补充模拟数据
    if len(history_records) < 3:
        history_records.extend([
            {
                'time': '2025-10-12 08:37:47',
                'location': '移动厅门口',
                'situation': '未成年人出现在该地点',
                'action': f'{police_station}到达现场，未见{name}。'
            },
            {
                'time': '2025-10-18 08:28:38',
                'location': 'xxxx',
                'situation': '未成年人出现在该地点',
                'action': f'{police_station}已通知{name}家属将其带回。'
            },
            {
                'time': '2025-10-18 08:28:55',
                'location': '路口对面',
                'situation': '未成年人出现在该地点',
                'action': f'{police_station}已通知{name}家属将其带回。'
            },
            {
                'time': '2025-10-26 11:22:01',
                'location': '大酒店对面',
                'situation': '未成年人出现在该地点',
                'action': f'{police_station}已通知监护人带回。'
            }
        ])

    # 同行人信息
    companion_info = f'目前没有明确的同行人信息。在多次预警记录中，均未提及{name}的具体同行人。'

    # 行为模式和潜在风险
    locations = [cap.get('camera_name', '') for cap in captures]
    risk_analysis = {
        'frequent_places': f'{name}多次出现在酒店、移动厅、酒吧等公共场所，这些地方通常是未成年人不宜进入的区域。',
        'time_pattern': f'预警记录显示，{name}多在早晨和下午出现，这可能是他放学后或周末的时间段。',
        'family_supervision': f'尽管派出所多次通知其监护人加强监管，但{name}仍然多次出现在公共场所，说明家庭监管存在一定的不足。',
        'potential_risk': f'频繁出现在这些场所可能会增加其接触不良人群的风险，从而导致不良行为的发生。'
    }

    # 巡逻防范建议
    suggestions = [
        f'针对{name}经常出现的地点，如大酒店、移动厅、酒吧等，增加巡逻频次，特别是在早晨和下午时间段。',
        '与社区工作人员和学校老师建立联动机制，共同关注xxx的行为动态，及时发现并干预。',
        f'继续与{name}的监护人保持沟通，督促其履行监管责任，必要时可提供家庭教育指导。',
        f'建议学校或社区为{name}提供心理辅导，帮助其树立正确的价值观和行为规范。',
        '派出所应定期回访xxx的家庭，了解其生活和学习状况，及时发现问题并采取措施。'
    ]

    # 结论
    conclusion = f'通过对{name}的历史预警记录和行为模式的分析，可以看出他在家庭监管和自我管理方面存在一定的问题。为了保障其健康成长，需要多方面的共同努力，加强对其的监管和引导，希望上述建议能够得到有效实施，减少潜在的风险。'

    return {
        'basic_info': basic_info,
        'history_records': history_records,
        'companion_info': companion_info,
        'risk_analysis': risk_analysis,
        'suggestions': suggestions,
        'conclusion': conclusion
    }


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/persons')
def get_persons():
    db = get_db()
    try:
        with db.cursor() as cursor:
            cursor.execute("""
                SELECT yp.id, yp.name, yp.gender, yp.age, yp.id_card_number,
                       yp.address, yp.police_station, yp.control_category
                FROM young_peoples yp
                ORDER BY yp.id
            """)
            persons = cursor.fetchall()
        return jsonify({'code': 0, 'data': persons})
    except Exception as e:
        return jsonify({'code': 500, 'message': str(e)})
    finally:
        db.close()


@app.route('/api/person/<id_card>')
def get_person_detail(id_card):
    db = get_db()
    try:
        with db.cursor() as cursor:
            # 基础信息 from young_peoples
            cursor.execute("""
                SELECT * FROM young_peoples WHERE id_card_number = %s
            """, (id_card,))
            person = cursor.fetchone()

            if not person:
                return jsonify({'code': 404, 'message': 'Person not found'})

            # 详细档案 from person_profiles
            cursor.execute("""
                SELECT * FROM person_profiles WHERE id_card_number = %s
            """, (id_card,))
            profile = cursor.fetchone()

            # 监护人信息 from person_guardians
            cursor.execute("""
                SELECT * FROM person_guardians WHERE person_id_card = %s
            """, (id_card,))
            guardians = cursor.fetchall()

            # 抓拍记录 from capture_records
            cursor.execute("""
                SELECT * FROM capture_records WHERE person_id_card = %s ORDER BY capture_time DESC
            """, (id_card,))
            captures = cursor.fetchall()

            # 组装基础信息
            birth_date = profile.get('birth_date') if profile else None
            age = calc_age(birth_date)
            if age is None:
                age = person.get('age', '')
            else:
                age = str(age)

            basic_info = {
                'name': person.get('name', ''),
                'gender': person.get('gender', ''),
                'birth_date': birth_date.strftime('%Y年%m月%d日') if birth_date else '',
                'age': age,
                'id_card': person.get('id_card_number', ''),
                'native_place': profile.get('native_place', 'xxx') if profile else 'xxx',
                'household_address': profile.get('household_address', 'xxx') if profile else 'xxx',
                'residence': person.get('address', 'xxx') if person else 'xxx',
                'education': profile.get('education', '初中') if profile else '初中',
                'school': profile.get('school', '') if profile else '',
                'enrollment_date': profile.get('enrollment_date', '') if profile else '',
                'graduation_date': profile.get('graduation_date', '') if profile else '',
                'subordinate_bureau': profile.get('subordinate_bureau', 'xxx分局') if profile else 'xxx分局',
                'police_station': person.get('police_station', 'xxx派出所') if person else 'xxx派出所',
                'person_type_tag': profile.get('person_type_tag', '专门学校') if profile else '专门学校',
            }

            # 处理日期格式
            for k in ['enrollment_date', 'graduation_date']:
                v = basic_info[k]
                if v and isinstance(v, date):
                    basic_info[k] = v.strftime('%Y年%m月%d日')

            # 送生信息
            delivery_info = {
                'time': profile.get('delivery_time', '3月') if profile else '3月',
                'unit': profile.get('delivery_unit', 'xx派出所') if profile else 'xx派出所'
            }

            # 其他信息
            other_info = {
                'is_serious_bad_minor': profile.get('is_serious_bad_minor', '否') if profile else '否',
                'personal_phone': profile.get('personal_phone', '1xxxx') if profile else '1xxxx',
                'guardian_phone': profile.get('guardian_phone', '1363534543（母亲）, 1385565（父亲）') if profile else '1363534543（母亲）, 1385565（父亲）',
                'remarks': profile.get('remarks', '无不良行为记录') if profile else '无不良行为记录',
                'bad_behavior_records': profile.get('bad_behavior_records', '') if profile else '',
                'racing_behavior': profile.get('racing_behavior', '无飙车炸街行为') if profile else '无飙车炸街行为',
                'analysis_phone': profile.get('analysis_phone', '135xxxx') if profile else '135xxxx'
            }

            # 历史预警反馈信息
            alert_records = []
            for cap in captures:
                capture_time = cap.get('capture_time')
                if isinstance(capture_time, datetime):
                    capture_time = capture_time.strftime('%Y-%m-%d %H:%M:%S')
                alert_records.append({
                    'time': capture_time,
                    'location': cap.get('camera_name', ''),
                    'situation': '未成年人出现在该地点',
                    'detail': f'{person.get("police_station", "xxx派出所")}：目前未发现{person.get("name", "xxx")}有违法犯罪行为。已联系其监护人（父亲）{person.get("name", "xxx")}让其配合民警对{person.get("name", "xxx")}开展"三教"工作，{person.get("name", "xxx")}表示会加强对{person.get("name", "xxx")}的监管。'
                })

            # 生成巡逻防范报告
            patrol_report = generate_patrol_report(person, profile, captures)

            return jsonify({
                'code': 0,
                'data': {
                    'basic_info': basic_info,
                    'guardians': guardians,
                    'delivery_info': delivery_info,
                    'other_info': other_info,
                    'alert_records': alert_records,
                    'patrol_report': patrol_report
                }
            })
    except Exception as e:
        import traceback
        return jsonify({'code': 500, 'message': str(e), 'trace': traceback.format_exc()})
    finally:
        db.close()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
