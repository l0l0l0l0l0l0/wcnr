# -*- coding: utf-8 -*-
"""
数据导入流程编排：暂存、合并、去重
"""

import logging
from datetime import datetime
from typing import Optional

from pymysql.cursors import DictCursor

from services.file_parser import (
    parse_upload_file,
    validate_population_row,
    validate_case_row,
    parse_involved_persons,
    POPULATION_COLUMN_MAP,
    CASE_COLUMN_MAP,
)

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def create_import_log(conn, source_system: str, file_name: str,
                      file_size: Optional[int], operator_id: Optional[int],
                      operator_name: Optional[str]) -> int:
    """创建导入日志记录，返回 log_id。"""
    with conn.cursor(DictCursor) as cursor:
        cursor.execute(
            """INSERT INTO data_import_logs
               (source_system, file_name, file_size, status, operator_id, operator_name, started_at)
               VALUES (%s, %s, %s, 'pending', %s, %s, %s)""",
            (source_system, file_name, file_size, operator_id, operator_name, datetime.now()),
        )
        conn.commit()
        return cursor.lastrowid


def update_import_log(conn, log_id: int, **kwargs):
    """更新导入日志。"""
    sets = ", ".join(f"{k} = %s" for k in kwargs)
    vals = list(kwargs.values()) + [log_id]
    with conn.cursor() as cursor:
        cursor.execute(f"UPDATE data_import_logs SET {sets} WHERE id = %s", vals)
        conn.commit()


def upload_population(conn, file_content: bytes, filename: str,
                      operator_id: Optional[int], operator_name: Optional[str]) -> dict:
    """人口数据上传：解析 → 校验 → 写入 staging → 返回预览。"""
    rows = parse_upload_file(file_content, filename, POPULATION_COLUMN_MAP)

    log_id = create_import_log(conn, "renkou", filename, len(file_content),
                               operator_id, operator_name)

    # 检查已有身份证号（population_info + young_peoples）
    with conn.cursor(DictCursor) as cursor:
        cursor.execute("SELECT id_card_number FROM population_info")
        existing_pop = {r["id_card_number"] for r in cursor.fetchall()}
        cursor.execute("SELECT id_card_number FROM young_peoples WHERE id_card_number IS NOT NULL")
        existing_yp = {r["id_card_number"] for r in cursor.fetchall()}
    existing = existing_pop | existing_yp

    valid_count = 0
    invalid_count = 0
    duplicate_count = 0
    validation_errors = []
    preview_rows = []

    with conn.cursor() as cursor:
        for row in rows:
            row_number = row.pop("_row_number", 0)
            is_valid, error_msg = validate_population_row(row)
            is_dup = row.get("id_card_number") in existing if is_valid else False

            if is_valid:
                valid_count += 1
                if is_dup:
                    duplicate_count += 1
            else:
                invalid_count += 1
                validation_errors.append({
                    "row_number": row_number,
                    "id_card_number": row.get("id_card_number", ""),
                    "name": row.get("name", ""),
                    "validation_error": error_msg,
                })

            cursor.execute(
                """INSERT INTO population_staging
                   (import_log_id, `row_number`, id_card_number, name, gender, age, address, contact,
                    is_valid, validation_error, is_duplicate)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (log_id, row_number, row.get("id_card_number"), row.get("name"),
                 row.get("gender"), row.get("age"), row.get("address"), row.get("contact"),
                 1 if is_valid else 0, error_msg, 1 if is_dup else 0),
            )

            if len(preview_rows) < 20:
                preview_rows.append({
                    "row_number": row_number,
                    **row,
                    "is_valid": is_valid,
                    "validation_error": error_msg,
                    "is_duplicate": is_dup,
                })

        conn.commit()

    update_import_log(conn, log_id, record_count=len(rows), status="pending")

    return {
        "import_log_id": log_id,
        "total_rows": len(rows),
        "valid_rows": valid_count,
        "invalid_rows": invalid_count,
        "duplicate_rows": duplicate_count,
        "preview": preview_rows,
        "validation_errors": validation_errors,
    }


def confirm_population_import(conn, log_id: int, skip_invalid: bool = True,
                              skip_duplicate: bool = False) -> dict:
    """确认人口数据导入：staging → population_info。"""
    update_import_log(conn, log_id, status="processing")

    try:
        conditions = ["import_log_id = %s"]
        params = [log_id]
        if skip_invalid:
            conditions.append("is_valid = 1")
        if skip_duplicate:
            conditions.append("is_duplicate = 0")

        where = " AND ".join(conditions)

        with conn.cursor(DictCursor) as cursor:
            cursor.execute(f"SELECT COUNT(*) AS cnt FROM population_staging WHERE {where}", params)
            to_import = cursor.fetchone()["cnt"]

            cursor.execute(
                f"""INSERT INTO population_info (id_card_number, name, gender, age, address, contact, import_log_id)
                    SELECT id_card_number, name, gender, age, address, contact, import_log_id
                    FROM population_staging
                    WHERE {where}
                    ON DUPLICATE KEY UPDATE
                        name = VALUES(name), gender = VALUES(gender), age = VALUES(age),
                        address = VALUES(address), contact = VALUES(contact),
                        import_log_id = VALUES(import_log_id)""",
                params,
            )
            imported = cursor.rowcount

            # 统计重复数
            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM population_staging WHERE import_log_id = %s AND is_duplicate = 1",
                (log_id,),
            )
            dup_count = cursor.fetchone()["cnt"]

            # 统计失败数
            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM population_staging WHERE import_log_id = %s AND is_valid = 0",
                (log_id,),
            )
            fail_count = cursor.fetchone()["cnt"]

            conn.commit()

        update_import_log(conn, log_id, status="completed",
                          success_count=to_import - dup_count if not skip_duplicate else imported,
                          duplicate_count=dup_count, fail_count=fail_count,
                          completed_at=datetime.now())

        return {
            "imported": imported,
            "duplicates_skipped": dup_count if skip_duplicate else 0,
            "failed": fail_count if skip_invalid else 0,
        }
    except Exception as e:
        update_import_log(conn, log_id, status="failed", error_message=str(e),
                          completed_at=datetime.now())
        raise


def upload_cases(conn, file_content: bytes, filename: str,
                 operator_id: Optional[int], operator_name: Optional[str]) -> dict:
    """案件数据上传：解析 → 校验 → 写入 staging → 返回预览。"""
    rows = parse_upload_file(file_content, filename, CASE_COLUMN_MAP)

    log_id = create_import_log(conn, "jingzong", filename, len(file_content),
                               operator_id, operator_name)

    with conn.cursor(DictCursor) as cursor:
        cursor.execute("SELECT case_number FROM cases")
        existing = {r["case_number"] for r in cursor.fetchall()}

    valid_count = 0
    invalid_count = 0
    duplicate_count = 0
    validation_errors = []
    preview_rows = []

    with conn.cursor() as cursor:
        for row in rows:
            row_number = row.pop("_row_number", 0)
            is_valid, error_msg = validate_case_row(row)
            is_dup = row.get("case_number") in existing if is_valid else False

            if is_valid:
                valid_count += 1
                if is_dup:
                    duplicate_count += 1
            else:
                invalid_count += 1
                validation_errors.append({
                    "row_number": row_number,
                    "case_number": row.get("case_number", ""),
                    "case_name": row.get("case_name", ""),
                    "validation_error": error_msg,
                })

            cursor.execute(
                """INSERT INTO case_staging
                   (import_log_id, `row_number`, case_number, case_name, case_type,
                    incident_time_str, incident_location, involved_persons,
                    is_valid, validation_error, is_duplicate)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (log_id, row_number, row.get("case_number"), row.get("case_name"),
                 row.get("case_type"), row.get("incident_time_str"),
                 row.get("incident_location"), row.get("involved_persons"),
                 1 if is_valid else 0, error_msg, 1 if is_dup else 0),
            )

            if len(preview_rows) < 20:
                preview_rows.append({
                    "row_number": row_number,
                    **row,
                    "is_valid": is_valid,
                    "validation_error": error_msg,
                    "is_duplicate": is_dup,
                })

        conn.commit()

    update_import_log(conn, log_id, record_count=len(rows), status="pending")

    return {
        "import_log_id": log_id,
        "total_rows": len(rows),
        "valid_rows": valid_count,
        "invalid_rows": invalid_count,
        "duplicate_rows": duplicate_count,
        "preview": preview_rows,
        "validation_errors": validation_errors,
    }


def confirm_case_import(conn, log_id: int, skip_invalid: bool = True,
                        skip_duplicate: bool = False) -> dict:
    """确认案件数据导入：staging → cases + case_persons。"""
    update_import_log(conn, log_id, status="processing")

    try:
        conditions = ["import_log_id = %s"]
        params = [log_id]
        if skip_invalid:
            conditions.append("is_valid = 1")
        if skip_duplicate:
            conditions.append("is_duplicate = 0")

        where = " AND ".join(conditions)

        with conn.cursor(DictCursor) as cursor:
            cursor.execute(f"SELECT * FROM case_staging WHERE {where}", params)
            staging_rows = cursor.fetchall()

        cases_imported = 0
        cases_updated = 0
        persons_linked = 0

        # 查询已有人员来源
        with conn.cursor(DictCursor) as cursor:
            cursor.execute("SELECT id_card_number FROM young_peoples WHERE id_card_number IS NOT NULL")
            yp_ids = {r["id_card_number"] for r in cursor.fetchall()}
            cursor.execute("SELECT id_card_number FROM population_info")
            pop_ids = {r["id_card_number"] for r in cursor.fetchall()}

        with conn.cursor() as cursor:
            for row in staging_rows:
                # 解析案发时间
                incident_time = _parse_datetime(row.get("incident_time_str"))

                # 插入/更新案件
                cursor.execute(
                    """INSERT INTO cases (case_number, case_name, case_type, incident_time,
                       incident_location, import_log_id)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE
                           case_name = VALUES(case_name), case_type = VALUES(case_type),
                           incident_time = VALUES(incident_time),
                           incident_location = VALUES(incident_location),
                           import_log_id = VALUES(import_log_id)""",
                    (row["case_number"], row.get("case_name"), row.get("case_type"),
                     incident_time, row.get("incident_location"), log_id),
                )

                if cursor.rowcount == 1:
                    cases_imported += 1
                else:
                    cases_updated += 1

                # 获取案件 ID
                with conn.cursor(DictCursor) as c2:
                    c2.execute("SELECT id FROM cases WHERE case_number = %s", (row["case_number"],))
                    case_row = c2.fetchone()
                if not case_row:
                    continue
                case_id = case_row["id"]

                # 解析涉案人员
                persons = parse_involved_persons(row.get("involved_persons"))
                for p in persons:
                    id_card = p.get("id_card_number")
                    p_name = p.get("person_name")
                    source = "unknown"
                    if id_card:
                        if id_card in yp_ids:
                            source = "young_peoples"
                        elif id_card in pop_ids:
                            source = "population_info"

                    cursor.execute(
                        """INSERT INTO case_persons (case_id, id_card_number, person_name, person_source)
                           VALUES (%s, %s, %s, %s)
                           ON DUPLICATE KEY UPDATE person_source = VALUES(person_source)""",
                        (case_id, id_card, p_name, source),
                    )
                    persons_linked += 1

            conn.commit()

        # 统计
        with conn.cursor(DictCursor) as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM case_staging WHERE import_log_id = %s AND is_duplicate = 1",
                (log_id,),
            )
            dup_count = cursor.fetchone()["cnt"]
            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM case_staging WHERE import_log_id = %s AND is_valid = 0",
                (log_id,),
            )
            fail_count = cursor.fetchone()["cnt"]

        update_import_log(conn, log_id, status="completed",
                          success_count=cases_imported + cases_updated,
                          duplicate_count=dup_count, fail_count=fail_count,
                          completed_at=datetime.now())

        return {
            "cases_imported": cases_imported,
            "cases_updated": cases_updated,
            "persons_linked": persons_linked,
            "failed": fail_count if skip_invalid else 0,
        }
    except Exception as e:
        update_import_log(conn, log_id, status="failed", error_message=str(e),
                          completed_at=datetime.now())
        raise


def promote_to_young_peoples(conn, id_card_numbers: list[str],
                              control_category: str,
                              operator_id: Optional[int] = None) -> dict:
    """将人口记录纳入布控：population_info → young_peoples。"""
    promoted = 0
    already_controlled = 0

    with conn.cursor(DictCursor) as cursor:
        # 获取 young_peoples 已有列
        cursor.execute("SHOW COLUMNS FROM young_peoples")
        yp_cols = {r["Field"] for r in cursor.fetchall()}

        for id_card in id_card_numbers:
            # 检查是否已在布控中
            cursor.execute(
                "SELECT id FROM young_peoples WHERE id_card_number = %s", (id_card,)
            )
            if cursor.fetchone():
                already_controlled += 1
                continue

            # 从 population_info 读取
            cursor.execute(
                "SELECT * FROM population_info WHERE id_card_number = %s", (id_card,)
            )
            pop = cursor.fetchone()
            if not pop:
                continue

            # 构建插入
            insert_cols = ["id_card_number"]
            insert_vals = [id_card]
            updates = []

            field_map = {
                "name": pop.get("name"),
                "gender": pop.get("gender"),
                "age": pop.get("age"),
                "address": pop.get("address"),
                "contact": pop.get("contact"),
            }

            for db_col, val in field_map.items():
                if db_col in yp_cols and val is not None:
                    insert_cols.append(db_col)
                    insert_vals.append(val)
                    if db_col != "id_card_number":
                        updates.append(f"{db_col} = VALUES({db_col})")

            if "control_category" in yp_cols:
                insert_cols.append("control_category")
                insert_vals.append(control_category)
                updates.append("control_category = VALUES(control_category)")

            if "data_source" in yp_cols:
                insert_cols.append("data_source")
                insert_vals.append("renkou")
                updates.append("data_source = VALUES(data_source)")

            if "source_import_log_id" in yp_cols:
                insert_cols.append("source_import_log_id")
                insert_vals.append(pop.get("import_log_id"))
                updates.append("source_import_log_id = VALUES(source_import_log_id)")

            placeholders = ",".join(["%s"] * len(insert_cols))
            col_names = ",".join(insert_cols)
            update_sql = ",".join(updates) if updates else "name = VALUES(name)"

            with conn.cursor() as c2:
                c2.execute(
                    f"INSERT INTO young_peoples ({col_names}) VALUES ({placeholders}) "
                    f"ON DUPLICATE KEY UPDATE {update_sql}",
                    insert_vals,
                )

            # 更新 population_info
            with conn.cursor() as c2:
                c2.execute(
                    "UPDATE population_info SET promoted = 1, promoted_at = %s WHERE id_card_number = %s",
                    (datetime.now(), id_card),
                )

            promoted += 1

        conn.commit()

    return {"promoted": promoted, "already_controlled": already_controlled}


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """尝试解析日期时间字符串。"""
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None
