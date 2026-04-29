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

from app.dependencies import get_db
from services.ai_portrait_queries import aggregate_person_data
from services.ai_llm import call_llm

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
    captures = data.get("capture_records") or []
    cases = data.get("cases") or []
    population = data.get("population_info")
    driver_stats = data.get("driver_stats") or {}
    face_records = data.get("face_records") or []

    lines = [
        "你是一名资深公安情报分析师。请根据以下人员数据，生成一份结构化的人员画像分析报告。",
        "",
        "【人员基础信息】",
        f"- 姓名: {_format_value(basic.get('name'))}",
        f"- 身份证号: {_format_value(basic.get('id_card_number'))}",
        f"- 性别: {_format_value(basic.get('gender'))}",
        f"- 年龄: {_format_value(basic.get('age'))}",
        f"- 联系方式: {_format_value(basic.get('contact'))}",
        f"- 居住地详址: {_format_value(basic.get('address'))}",
        f"- 人员类别: {_format_value(basic.get('person_category'))}",
        f"- 涉案前科: {_format_value(basic.get('criminal_record'))}",
        f"- 派出所: {_format_value(basic.get('police_station'))}",
        f"- 警务区: {_format_value(basic.get('police_district'))}",
        "",
        "【管控信息】",
        f"- 管控类别: {_format_value(basic.get('control_category'))}",
        f"- 纳管时间: {_format_value(basic.get('control_time'))}",
        f"- 数据来源: {_format_value(basic.get('data_source'))}",
        f"- 更新时间: {_format_value(basic.get('update_time'))}",
        "",
    ]

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
        "请严格按以下格式输出分析报告：",
        "",
        "1. 人员画像摘要（200字以内）",
        "2. 风险等级评估（高/中/低，并说明依据）",
        "3. 行为特征分析",
        "4. 活动轨迹总结",
        "5. 关联案件分析",
        "6. 管控建议",
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


@router.post("/analyze")
def analyze_person(request: AnalyzeRequest):
    """根据身份证号聚合多表数据，调用 LLM 生成人员画像分析。"""
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
