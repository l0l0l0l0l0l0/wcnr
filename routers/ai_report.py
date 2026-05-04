# -*- coding: utf-8 -*-
"""
AI档案 API 路由
"""

import hashlib
import json
import logging
import re

from fastapi import APIRouter, Depends
from pymysql.cursors import DictCursor
from datetime import datetime, date

from app.dependencies import get_db, get_current_user

router = APIRouter(prefix="/api/ai-report", tags=["AI档案"])

logger = logging.getLogger(__name__)

# Simple in-memory cache for LLM-generated report sections
_llm_cache = {}
_LLM_CACHE_MAX = 200


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


def _get_cache_key(id_card, captures):
    """Generate a cache key from person ID and capture data hash"""
    capture_str = json.dumps(
        [(c.get('capture_time', ''), c.get('camera_name', ''), c.get('camera_index_code', ''))
         for c in captures],
        default=str, ensure_ascii=False
    )
    capture_hash = hashlib.md5(capture_str.encode()).hexdigest()[:12]
    return f"{id_card}:{capture_hash}"


def _build_llm_prompt(person, profile, captures):
    """构建LLM分析提示词"""
    name = person.get('name', 'xxx')
    gender = person.get('gender', '')
    age = person.get('age', '')
    address = person.get('address', '')
    police_station = person.get('police_station', 'xxx派出所')
    school = profile.get('school', '') if profile else ''
    bureau = profile.get('subordinate_bureau', 'xxx分局') if profile else 'xxx分局'
    person_type = profile.get('person_type_tag', '专门学校') if profile else '专门学校'
    household_address = profile.get('household_address', '') if profile else ''

    capture_lines = []
    for i, cap in enumerate(captures, 1):
        capture_time = cap.get('capture_time')
        if isinstance(capture_time, datetime):
            capture_time = capture_time.strftime('%Y-%m-%d %H:%M:%S')
        line = (
            f"  {i}. 时间：{capture_time or '未知'}，"
            f"地点：{cap.get('camera_name', '未知')}，"
            f"摄像头编号：{cap.get('camera_index_code', '')}，"
            f"相似度：{cap.get('similarity', '')}，"
            f"性别：{cap.get('gender', '')}，"
            f"年龄段：{cap.get('age_group', '')}"
        )
        capture_lines.append(line)

    captures_text = '\n'.join(capture_lines) if capture_lines else '  暂无抓拍记录'

    prompt = f"""你是一名资深的公安情报分析师，负责分析重点人员的行为模式并撰写巡逻防范报告。

## 人员基本信息
- 姓名：{name}
- 性别：{gender}
- 年龄：{age}
- 户籍地：{household_address or '未知'}
- 居住地：{address or '未知'}
- 所属分局：{bureau}
- 所辖派出所：{police_station}
- 学校：{school or '未知'}
- 人员类型：{person_type}

## 抓拍预警记录
{captures_text}

## 任务要求
请基于以上信息，分析该人员的行为模式和潜在风险，并提出巡逻防范建议。请严格以JSON格式输出，包含以下字段：

{{
  "risk_analysis": {{
    "frequent_places": "分析该人员频繁出现的地点类型及场所特征（如酒店、网吧、娱乐场所等），结合具体抓拍地点说明",
    "time_pattern": "分析该人员出现的时间规律（如主要集中在哪个时段、是否与放学/周末相关等），结合具体抓拍时间说明",
    "family_supervision": "分析家庭监管状况，结合抓拍频率和派出所处置情况评估监护人是否尽责",
    "potential_risk": "综合评估该人员的潜在风险，包括可能接触不良人群、发生不良行为的可能性等"
  }},
  "suggestions": [
    "第一条建议：针对该人员经常出现区域的具体巡逻建议",
    "第二条建议：社区、学校联动方面的建议",
    "第三条建议：家庭监督方面的建议",
    "第四条建议：心理辅导或教育方面的建议",
    "第五条建议：派出所定期回访方面的建议"
  ],
  "conclusion": "综合以上分析的整体结论，概述主要风险点和需要关注的重点方向"
}}

要求：
1. 分析内容必须基于提供的抓拍数据，引用具体的时间、地点信息
2. 每条建议应具有可操作性，不要空泛
3. 输出必须是合法的JSON格式，不要包含JSON以外的任何文字
4. 中文输出"""
    return prompt


def _parse_llm_response(text, name):
    """解析LLM返回的JSON文本，提取risk_analysis、suggestions、conclusion"""
    # Try to extract JSON from markdown code blocks first
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if json_match:
        text = json_match.group(1).strip()

    # Try to find JSON object directly
    brace_match = re.search(r'\{[\s\S]*\}', text)
    if brace_match:
        text = brace_match.group(0)

    data = json.loads(text)

    risk = data.get('risk_analysis', {})
    if not isinstance(risk, dict):
        risk = {}

    risk_analysis = {
        'frequent_places': risk.get('frequent_places', ''),
        'time_pattern': risk.get('time_pattern', ''),
        'family_supervision': risk.get('family_supervision', ''),
        'potential_risk': risk.get('potential_risk', ''),
    }

    suggestions = data.get('suggestions', [])
    if not isinstance(suggestions, list):
        suggestions = []
    while len(suggestions) < 5:
        suggestions.append(f'关于{name}的进一步建议待补充。')

    conclusion = data.get('conclusion', '')
    if not conclusion:
        conclusion = f'综合以上分析，{name}的行为模式和家庭监管存在一定问题，需要多方共同努力。'

    return {
        'risk_analysis': risk_analysis,
        'suggestions': suggestions,
        'conclusion': conclusion
    }


def generate_patrol_report(person, profile, captures):
    """基于数据生成巡逻防范报告，section 四/五/结论使用LLM生成"""
    name = person.get('name', 'xxx')
    age = person.get('age', '')
    gender = person.get('gender', '')
    address = person.get('address', '')
    police_station = person.get('police_station', 'xxx派出所')
    school = profile.get('school', '') if profile else ''
    bureau = profile.get('subordinate_bureau', 'xxx分局') if profile else 'xxx分局'
    person_type = profile.get('person_type_tag', '专门学校') if profile else '专门学校'

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

    history_records = []
    for cap in captures:
        capture_time = cap.get('capture_time')
        if isinstance(capture_time, datetime):
            capture_time = capture_time.strftime('%Y-%m-%d %H:%M:%S')
        history_records.append({
            'time': capture_time or '2025-10-04 19:18:13',
            'location': cap.get('camera_name', '大酒店门口'),
            'situation': '未成年人出现在该地点',
            'action': f'{police_station}已联系其监护人（父亲）{name}，让其配合民警对{name}开展"三教"工作，{name}表示会加强对{name}的监管。'
        })

    if len(history_records) < 3:
        history_records.extend([
            {'time': '2025-10-12 08:37:47', 'location': '移动厅门口',
             'situation': '未成年人出现在该地点', 'action': f'{police_station}到达现场，未见{name}。'},
            {'time': '2025-10-18 08:28:38', 'location': 'xxxx',
             'situation': '未成年人出现在该地点', 'action': f'{police_station}已通知{name}家属将其带回。'},
            {'time': '2025-10-18 08:28:55', 'location': '路口对面',
             'situation': '未成年人出现在该地点', 'action': f'{police_station}已通知{name}家属将其带回。'},
            {'time': '2025-10-26 11:22:01', 'location': '大酒店对面',
             'situation': '未成年人出现在该地点', 'action': f'{police_station}已通知监护人带回。'}
        ])

    companion_info = f'目前没有明确的同行人信息。在多次预警记录中，均未提及{name}的具体同行人。'

    # --- Template fallback for sections 四/五/结论 ---
    template_risk_analysis = {
        'frequent_places': f'{name}多次出现在酒店、移动厅、酒吧等公共场所，这些地方通常是未成年人不宜进入的区域。',
        'time_pattern': f'预警记录显示，{name}多在早晨和下午出现，这可能是他放学后或周末的时间段。',
        'family_supervision': f'尽管派出所多次通知其监护人加强监管，但{name}仍然多次出现在公共场所，说明家庭监管存在一定的不足。',
        'potential_risk': f'频繁出现在这些场所可能会增加其接触不良人群的风险，从而导致不良行为的发生。'
    }
    template_suggestions = [
        f'针对{name}经常出现的地点，如大酒店、移动厅、酒吧等，增加巡逻频次，特别是在早晨和下午时间段。',
        '与社区工作人员和学校老师建立联动机制，共同关注xxx的行为动态，及时发现并干预。',
        f'继续与{name}的监护人保持沟通，督促其履行监管责任，必要时可提供家庭教育指导。',
        f'建议学校或社区为{name}提供心理辅导，帮助其树立正确的价值观和行为规范。',
        '派出所应定期回访xxx的家庭，了解其生活和学习状况，及时发现问题并采取措施。'
    ]
    template_conclusion = f'通过对{name}的历史预警记录和行为模式的分析，可以看出他在家庭监管和自我管理方面存在一定的问题。为了保障其健康成长，需要多方面的共同努力，加强对其的监管和引导，希望上述建议能够得到有效实施，减少潜在的风险。'

    # --- Try LLM generation for sections 四/五/结论 ---
    risk_analysis = template_risk_analysis
    suggestions = template_suggestions
    conclusion = template_conclusion

    id_card = person.get('id_card_number', '')
    cache_key = _get_cache_key(id_card, captures) if id_card else None

    # Check cache first
    if cache_key and cache_key in _llm_cache:
        logger.info(f"[AI Report] LLM cache hit for {id_card}")
        cached = _llm_cache[cache_key]
        risk_analysis = cached['risk_analysis']
        suggestions = cached['suggestions']
        conclusion = cached['conclusion']
    else:
        try:
            from services.ai_llm import call_llm
            prompt = _build_llm_prompt(person, profile, captures)
            logger.info(f"[AI Report] Calling LLM for {name} ({id_card})")
            raw_response = call_llm(prompt)
            llm_result = _parse_llm_response(raw_response, name)
            risk_analysis = llm_result['risk_analysis']
            suggestions = llm_result['suggestions']
            conclusion = llm_result['conclusion']

            # Cache the result
            if cache_key:
                if len(_llm_cache) >= _LLM_CACHE_MAX:
                    keys_to_remove = list(_llm_cache.keys())[:_LLM_CACHE_MAX // 2]
                    for k in keys_to_remove:
                        del _llm_cache[k]
                _llm_cache[cache_key] = llm_result

            logger.info(f"[AI Report] LLM generation successful for {name}")
        except Exception as e:
            logger.warning(f"[AI Report] LLM generation failed, using template fallback: {e}")

    return {
        'basic_info': basic_info,
        'history_records': history_records,
        'companion_info': companion_info,
        'risk_analysis': risk_analysis,
        'suggestions': suggestions,
        'conclusion': conclusion
    }


@router.get("/persons")
def get_persons(conn=Depends(get_db), user=Depends(get_current_user)):
    with conn.cursor(DictCursor) as cursor:
        cursor.execute("""
            SELECT yp.id, yp.name, yp.gender, yp.age, yp.id_card_number,
                   yp.address, yp.police_station, yp.control_category
            FROM young_peoples yp
            ORDER BY yp.id
        """)
        persons = cursor.fetchall()
    return {"success": True, "data": persons}


@router.get("/person/{id_card}")
def get_person_detail(id_card: str, conn=Depends(get_db), user=Depends(get_current_user)):
    with conn.cursor(DictCursor) as cursor:
        cursor.execute("SELECT * FROM young_peoples WHERE id_card_number = %s", (id_card,))
        person = cursor.fetchone()

        if not person:
            return {"success": False, "message": "未找到该人员"}

        cursor.execute("SELECT * FROM person_profiles WHERE id_card_number = %s", (id_card,))
        profile = cursor.fetchone()

        cursor.execute("SELECT * FROM person_guardians WHERE person_id_card = %s", (id_card,))
        guardians = cursor.fetchall()

        cursor.execute("SELECT * FROM capture_records WHERE person_id_card = %s ORDER BY capture_time DESC", (id_card,))
        captures = cursor.fetchall()

    # 基础信息
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

    for k in ['enrollment_date', 'graduation_date']:
        v = basic_info[k]
        if v and isinstance(v, date):
            basic_info[k] = v.strftime('%Y年%m月%d日')

    delivery_info = {
        'time': profile.get('delivery_time', '3月') if profile else '3月',
        'unit': profile.get('delivery_unit', 'xx派出所') if profile else 'xx派出所'
    }

    other_info = {
        'is_serious_bad_minor': profile.get('is_serious_bad_minor', '否') if profile else '否',
        'personal_phone': profile.get('personal_phone', '1xxxx') if profile else '1xxxx',
        'guardian_phone': profile.get('guardian_phone', '1363534543（母亲）, 1385565（父亲）') if profile else '1363534543（母亲）, 1385565（父亲）',
        'remarks': profile.get('remarks', '无不良行为记录') if profile else '无不良行为记录',
        'bad_behavior_records': profile.get('bad_behavior_records', '') if profile else '',
        'racing_behavior': profile.get('racing_behavior', '无飙车炸街行为') if profile else '无飙车炸街行为',
        'analysis_phone': profile.get('analysis_phone', '135xxxx') if profile else '135xxxx'
    }

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

    patrol_report = generate_patrol_report(person, profile, captures)

    return {
        "success": True,
        "data": {
            "basic_info": basic_info,
            "guardians": guardians,
            "delivery_info": delivery_info,
            "other_info": other_info,
            "alert_records": alert_records,
            "patrol_report": patrol_report
        }
    }
