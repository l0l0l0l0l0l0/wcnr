# -*- coding: utf-8 -*-
"""
AI 画像路由
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from pymysql.cursors import DictCursor
from pymysql import err as pymysql_err

from app.dependencies import get_db
from services.ai_portrait_queries import aggregate_person_data
from services.ai_llm import call_llm
from services.db import get_table_columns

router = APIRouter(prefix="/api/ai-portrait")
logger = logging.getLogger(__name__)


# ---------------- Pydantic Models ----------------

class AnalyzeRequest(BaseModel):
    id_card_number: str


# ---------------- Prompt Builder ----------------

def _format_value(v) -> str:
    if v is None:
        return "无"
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    return str(v)


def build_analysis_prompt(data: dict) -> str:
    basic = data.get("basic_info") or {}
    guardians = data.get("guardians") or []
    alert_feedback = data.get("alert_feedback") or []
    captures = data.get("capture_records") or []
    cases = data.get("cases") or []
    population = data.get("population_info")
    driver_stats = data.get("driver_stats") or {}
    face_records = data.get("face_records") or []

    lines = [
        "你是一名资深公安情报分析师。请根据以下人员数据，生成一份结构化的巡逻防范报告。",
        "",
        "【人员基础信息】",
        f"- 姓名: {_format_value(basic.get('name'))}",
        f"- 身份证号: {_format_value(basic.get('id_card_number'))}",
        f"- 性别: {_format_value(basic.get('gender'))}",
        f"- 出生日期: {_format_value(basic.get('birth_date'))}",
        f"- 年龄: {_format_value(basic.get('age'))}",
        f"- 联系方式: {_format_value(basic.get('contact'))}",
        f"- 居住地详址: {_format_value(basic.get('address'))}",
        f"- 户籍地: {_format_value(basic.get('household_address'))}",
        f"- 籍贯: {_format_value(basic.get('native_place'))}",
        f"- 学历: {_format_value(basic.get('education'))}",
        f"- 学校: {_format_value(basic.get('school'))}",
        f"- 入学时间: {_format_value(basic.get('enrollment_date'))}",
        f"- 离校时间: {_format_value(basic.get('graduation_date'))}",
        f"- 人员类别: {_format_value(basic.get('person_category'))}",
        f"- 人员类型标签: {_format_value(basic.get('person_type_tag'))}",
        f"- 涉案前科: {_format_value(basic.get('criminal_record'))}",
        f"- 派出所: {_format_value(basic.get('police_station'))}",
        f"- 所属分局: {_format_value(basic.get('subordinate_bureau'))}",
        f"- 警务区: {_format_value(basic.get('police_district'))}",
        "",
        "【管控信息】",
        f"- 管控类别: {_format_value(basic.get('control_category'))}",
        f"- 纳管时间: {_format_value(basic.get('control_time'))}",
        f"- 数据来源: {_format_value(basic.get('data_source'))}",
        f"- 更新时间: {_format_value(basic.get('update_time'))}",
        "",
    ]

    if guardians:
        lines.append("【监护人信息】")
        for g in guardians:
            lines.append(
                f"- {g.get('guardian_type')}: {g.get('name')}, "
                f"联系方式: {_format_value(g.get('contact'))}, "
                f"身份证: {_format_value(g.get('id_card_number'))}, "
                f"关系: {_format_value(g.get('relation'))}, "
                f"居住地: {_format_value(g.get('address'))}"
            )
        lines.append("")

    if basic.get("delivery_time") or basic.get("delivery_unit"):
        lines.extend([
            "【送生信息】",
            f"- 送生时间: {_format_value(basic.get('delivery_time'))}",
            f"- 送生单位: {_format_value(basic.get('delivery_unit'))}",
            "",
        ])

    ext_lines = []
    if basic.get("is_serious_bad_minor"):
        ext_lines.append(f"- 是否严重不良未成年人: {_format_value(basic.get('is_serious_bad_minor'))}")
    if basic.get("personal_phone"):
        ext_lines.append(f"- 本人电话: {_format_value(basic.get('personal_phone'))}")
    if basic.get("guardian_phone"):
        ext_lines.append(f"- 监护人电话: {_format_value(basic.get('guardian_phone'))}")
    if basic.get("bad_behavior_records"):
        ext_lines.append(f"- 不良行为记录: {_format_value(basic.get('bad_behavior_records'))}")
    if basic.get("racing_behavior"):
        ext_lines.append(f"- 飙车炸街行为: {_format_value(basic.get('racing_behavior'))}")
    if basic.get("analysis_phone"):
        ext_lines.append(f"- 综合分析手机号: {_format_value(basic.get('analysis_phone'))}")
    if basic.get("remarks"):
        ext_lines.append(f"- 备注: {_format_value(basic.get('remarks'))}")
    if ext_lines:
        lines.extend(["【其他信息】"] + ext_lines + [""])

    if population:
        lines.extend([
            "【人口系统信息】",
            f"- 姓名: {_format_value(population.get('name'))}",
            f"- 性别: {_format_value(population.get('gender'))}",
            f"- 年龄: {_format_value(population.get('age'))}",
            f"- 住址: {_format_value(population.get('address'))}",
            f"- 联系方式: {_format_value(population.get('contact'))}",
            f"- 是否已纳入布控: {'是' if population.get('promoted') else '否'}",
            "",
        ])

    lines.extend([
        "【抓拍记录统计】",
        f"- 总抓拍记录数: {len(captures)}",
        f"- 驾驶员识别: 总识别次数 {_format_value(driver_stats.get('total_captures'))}, "
        f"驾驶员 {_format_value(driver_stats.get('driver_count'))} 次, "
        f"乘客 {_format_value(driver_stats.get('passenger_count'))} 次",
        "",
    ])

    if alert_feedback:
        lines.append("【历史预警反馈记录】")
        for i, af in enumerate(alert_feedback[:20], 1):
            lines.append(
                f"{i}. 时间: {_format_value(af.get('time'))}, "
                f"地点: {_format_value(af.get('location'))}, "
                f"情况: {_format_value(af.get('situation'))}, "
                f"处理: {_format_value(af.get('handling'))}"
            )
        lines.append("")

    if captures:
        lines.append("【近期抓拍记录 Top 20】")
        for i, c in enumerate(captures[:20], 1):
            lines.append(
                f"{i}. 时间: {_format_value(c.get('capture_time'))}, "
                f"摄像头: {_format_value(c.get('camera_name'))}, "
                f"相似度: {_format_value(c.get('similarity'))}, "
                f"车牌: {_format_value(c.get('plate_no'))}, "
                f"年龄组: {_format_value(c.get('age_group'))}, "
                f"戴眼镜: {_format_value(c.get('glass'))}"
            )
        lines.append("")

    if face_records:
        lines.append("【人脸记录 Top 10】")
        for i, f in enumerate(face_records[:10], 1):
            lines.append(
                f"{i}. 时间: {_format_value(f.get('captureTime'))}, "
                f"摄像头: {_format_value(f.get('cameraName'))}, "
                f"车牌: {_format_value(f.get('plateNo'))}, "
                f"相似度: {_format_value(f.get('similarity'))}"
            )
        lines.append("")

    if cases:
        lines.append("【关联案件】")
        for i, case in enumerate(cases, 1):
            lines.append(
                f"{i}. 案件编号: {_format_value(case.get('case_number'))}, "
                f"案件名称: {_format_value(case.get('case_name'))}, "
                f"案件类型: {_format_value(case.get('case_type'))}, "
                f"案发时间: {_format_value(case.get('incident_time'))}, "
                f"案发地点: {_format_value(case.get('incident_location'))}, "
                f"涉案角色: {_format_value(case.get('role_in_case'))}"
            )
            if case.get("description"):
                lines.append(f"   描述: {_format_value(case.get('description'))}")
        lines.append("")
    else:
        lines.extend(["【关联案件】", "无关联案件记录", ""])

    lines.extend([
        "请严格按以下格式输出巡逻防范报告：",
        "",
        "一、基本信息",
        "（总结该人员的基础信息、家庭背景、监护情况、就学情况等，150字以内）",
        "",
        "二、历史预警记录",
        "（列出该人员近期历史预警的时间、地点、情况、处理结果，按时间倒序）",
        "",
        "三、同行人信息",
        "（分析抓拍记录中是否存在同行人，如有请描述；如没有请说明）",
        "",
        "四、行为模式和潜在风险",
        "（基于历史预警和抓拍记录，分析该人员的行为模式、时间规律、频繁出现地点、潜在风险等）",
        "",
        "五、巡逻防范建议",
        "（提出具体的巡逻防范建议，包括重点时段、重点区域、家庭监管、社区联动、心理辅导等方面）",
        "",
        "结论",
        "（总结该人员的整体风险状况，提出下一步工作建议）",
        "",
        "注意：",
        "- 基于客观数据进行分析，避免无依据的推测。",
        "- 如果数据不足，请明确说明。",
        "- 风险等级必须有明确的数据支撑。",
    ])

    return "\n".join(lines)


# ---------------- Endpoints ----------------

@router.get("/persons")
def list_persons(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = Query(None),
    conn=Depends(get_db),
):
    """查询布控人员列表，支持关键词搜索。"""
    with conn.cursor(DictCursor) as cursor:
        where_clauses = []
        params = []

        if keyword:
            where_clauses.append(
                "(name LIKE %s OR id_card_number LIKE %s OR control_category LIKE %s OR police_station LIKE %s)"
            )
            like_kw = f"%{keyword}%"
            params.extend([like_kw, like_kw, like_kw, like_kw])

        where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

        cursor.execute(f"SELECT COUNT(*) AS cnt FROM young_peoples{where_sql}", params)
        total = cursor.fetchone()["cnt"]

        pages = max(1, (total + per_page - 1) // per_page)
        offset = (page - 1) * per_page

        sql = f"""
            SELECT id, name, gender, id_card_number, age, address,
                   person_category, control_category, police_station,
                   criminal_record, person_face_url
            FROM young_peoples
            {where_sql}
            ORDER BY id DESC
            LIMIT %s OFFSET %s
        """
        cursor.execute(sql, params + [per_page, offset])
        rows = cursor.fetchall()

    return {
        "success": True,
        "data": {
            "items": rows,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
        },
    }


def _safe_strftime(val, fmt="%Y-%m-%d"):
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.strftime(fmt)
    return str(val)


def _table_exists(cursor, table_name: str) -> bool:
    try:
        cursor.execute("SHOW TABLES LIKE %s", (table_name,))
        return cursor.fetchone() is not None
    except Exception:
        return False


def _query_person(cursor, id_card: str, yp_cols: set, pp_cols: set):
    """查询 young_peoples + person_profiles，兼容缺失字段。"""
    yp_base_fields = [
        "id", "name", "gender", "contact", "id_card_number", "address",
        "person_category", "criminal_record", "update_time",
        "person_face_url", "age", "police_station", "police_district",
        "control_category", "control_time",
    ]
    yp_extra_fields = ["data_source"]
    yp_select = ", ".join(
        [f"yp.{c}" for c in yp_base_fields if c in yp_cols] +
        [f"yp.{c}" for c in yp_extra_fields if c in yp_cols]
    )

    pp_fields = [
        "birth_date", "native_place", "household_address", "education",
        "school", "enrollment_date", "graduation_date", "subordinate_bureau",
        "person_type_tag", "delivery_time", "delivery_unit",
        "is_serious_bad_minor", "personal_phone", "guardian_phone",
        "remarks", "bad_behavior_records", "racing_behavior", "analysis_phone",
    ]
    pp_select = ", ".join([f"pp.{c}" for c in pp_fields if c in pp_cols])

    has_pp = _table_exists(cursor, "person_profiles") and pp_select
    sql = f"SELECT {yp_select}"
    if has_pp:
        sql += f", {pp_select}"
    sql += " FROM young_peoples yp"
    if has_pp:
        sql += " LEFT JOIN person_profiles pp ON pp.id_card_number = yp.id_card_number"
    sql += " WHERE yp.id_card_number = %s LIMIT 1"

    cursor.execute(sql, (id_card,))
    return cursor.fetchone()


@router.get("/profile")
def get_profile(
    id_card_number: str = Query(..., description="身份证号"),
    conn=Depends(get_db),
):
    """获取人员结构化档案数据（个人简介 + 历史预警反馈）。"""
    id_card = id_card_number.strip()
    if not id_card:
        return {"success": False, "message": "身份证号不能为空"}

    try:
        with conn.cursor(DictCursor) as cursor:
            # 1) 查询 young_peoples 基础信息
            yp_cols = get_table_columns(conn, "young_peoples")
            pp_cols = get_table_columns(conn, "person_profiles")
            person = _query_person(cursor, id_card, yp_cols, pp_cols)
            if not person:
                return {"success": False, "message": "未找到该人员"}

            # 2) 查询监护人（表可能不存在）
            guardians = []
            try:
                if _table_exists(cursor, "person_guardians"):
                    cursor.execute(
                        """
                        SELECT id, guardian_type, name, contact, id_card_number, address, relation
                        FROM person_guardians
                        WHERE person_id_card = %s
                        ORDER BY FIELD(guardian_type, '母亲', '父亲', '其他'), id ASC
                        """,
                        (id_card,),
                    )
                    guardians = cursor.fetchall()
            except Exception as e:
                logger.warning(f"查询监护人失败: {e}")

            # 3) 查询历史预警反馈（alert_process_logs 可能不存在）
            alert_feedback = []
            try:
                if _table_exists(cursor, "alert_process_logs"):
                    cursor.execute(
                        """
                        SELECT cr.capture_time, cr.camera_name, cr.camera_index_code,
                               cr.plate_no, cr.capture_id,
                               apl.feedback_content, apl.handler_name, apl.created_at AS feedback_time
                        FROM capture_records cr
                        LEFT JOIN alert_process_logs apl ON apl.record_id = cr.id AND apl.action = 'feedback'
                        WHERE cr.person_id_card = %s AND cr.is_processed = 2
                        ORDER BY cr.capture_time DESC
                        LIMIT 50
                        """,
                        (id_card,),
                    )
                    alert_rows = cursor.fetchall()
                    for r in alert_rows:
                        if not r.get("feedback_content"):
                            continue
                        alert_feedback.append({
                            "time": _safe_strftime(r.get("capture_time"), "%Y-%m-%d %H:%M:%S") or "",
                            "location": r.get("camera_name") or "",
                            "camera_index_code": r.get("camera_index_code") or "",
                            "situation": "未成年人出现在该地点",
                            "handling": r.get("feedback_content") or "",
                            "handler_name": r.get("handler_name") or "",
                            "feedback_time": _safe_strftime(r.get("feedback_time"), "%Y-%m-%d %H:%M:%S") or "",
                        })
            except Exception as e:
                logger.warning(f"查询历史预警反馈失败: {e}")

    except pymysql_err.OperationalError as e:
        logger.exception("数据库操作异常")
        return {"success": False, "message": f"数据库错误: {e}"}
    except Exception as e:
        logger.exception("获取档案失败")
        return {"success": False, "message": f"查询失败: {e}"}

    basic = {
        "name": person.get("name"),
        "gender": person.get("gender"),
        "id_card_number": person.get("id_card_number"),
        "age": person.get("age"),
        "address": person.get("address"),
        "contact": person.get("contact"),
        "police_station": person.get("police_station"),
        "police_district": person.get("police_district"),
        "control_category": person.get("control_category"),
        "person_category": person.get("person_category"),
        "criminal_record": person.get("criminal_record"),
        "person_face_url": person.get("person_face_url"),
        "birth_date": _safe_strftime(person.get("birth_date")),
        "native_place": person.get("native_place"),
        "household_address": person.get("household_address"),
        "education": person.get("education"),
        "school": person.get("school"),
        "enrollment_date": _safe_strftime(person.get("enrollment_date")),
        "graduation_date": _safe_strftime(person.get("graduation_date")),
        "subordinate_bureau": person.get("subordinate_bureau"),
        "person_type_tag": person.get("person_type_tag"),
        "delivery_time": person.get("delivery_time"),
        "delivery_unit": person.get("delivery_unit"),
        "is_serious_bad_minor": person.get("is_serious_bad_minor"),
        "personal_phone": person.get("personal_phone"),
        "guardian_phone": person.get("guardian_phone"),
        "remarks": person.get("remarks"),
        "bad_behavior_records": person.get("bad_behavior_records"),
        "racing_behavior": person.get("racing_behavior"),
        "analysis_phone": person.get("analysis_phone"),
        "data_source": person.get("data_source"),
    }

    return {
        "success": True,
        "data": {
            "basic_info": basic,
            "guardians": guardians,
            "alert_feedback": alert_feedback,
        },
    }


@router.post("/analyze")
def analyze_person(request: AnalyzeRequest):
    """根据身份证号聚合多表数据，调用 LLM 生成巡逻防范报告。"""
    id_card = request.id_card_number.strip()
    if not id_card:
        return {"success": False, "message": "身份证号不能为空"}

    try:
        person_data = aggregate_person_data(id_card)
    except ValueError as e:
        return {"success": False, "message": str(e)}
    except Exception as e:
        logger.exception("聚合人员数据失败")
        return {"success": False, "message": f"数据查询失败: {e}"}

    prompt = build_analysis_prompt(person_data)

    try:
        analysis = call_llm(prompt)
    except RuntimeError as e:
        logger.error(f"LLM 调用失败: {e}")
        return {"success": False, "message": f"AI 分析服务异常: {e}"}
    except Exception as e:
        logger.exception("LLM 调用异常")
        return {"success": False, "message": f"AI 分析服务异常: {e}"}

    basic = person_data.get("basic_info") or {}
    return {
        "success": True,
        "data": {
            "analysis": analysis,
            "person_summary": {
                "name": basic.get("name"),
                "id_card_number": basic.get("id_card_number"),
                "gender": basic.get("gender"),
                "age": basic.get("age"),
                "control_category": basic.get("control_category"),
                "police_station": basic.get("police_station"),
                "criminal_record": basic.get("criminal_record"),
                "person_face_url": basic.get("person_face_url"),
            },
        },
    }
