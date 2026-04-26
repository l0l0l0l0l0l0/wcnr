import json
import os
from datetime import datetime, timedelta

import requests


def queryPersonByAttrWithPage(person_lib_id, human_ids, name, register_gender, certificate_type, certificate_number,
                         native_county_code, residence_county_code, begin_time, end_time, page_number, page_size):
    now = datetime.now()
    tzoffset = '+08:00'

    if end_time:
        end_time_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
    else:
        end_time_dt = now

    if begin_time:
        begin_time_dt = datetime.fromisoformat(begin_time.replace('Z', '+00:00'))
    else:
        begin_time_dt = end_time_dt - timedelta(hours=24 * 31)

    formatted_begin_time = begin_time_dt.strftime('%Y-%m-%dT%H:%M:%S') + tzoffset
    formatted_end_time = end_time_dt.strftime('%Y-%m-%dT%H:%M:%S') + tzoffset

    payload = {
        "pageNo": page_number,
        "pageSize": page_size,
        "personLibId": person_lib_id,
    }

    optional_fields = {
        "humanIds": human_ids,
        "name": name,
        "registerGender": register_gender,
        "certificateType": certificate_type,
        "certificateNumber": certificate_number,
        "nativeCountyCode": native_county_code,
        "residenceCountyCode": residence_county_code,
        "beginTime": formatted_begin_time,
        "endTime": formatted_end_time,
    }

    payload.update({k: v for k, v in optional_fields.items() if v is not None})

    logger.info(f"请求体: {json.dumps(payload, indent=2, ensure_ascii=False)}")

    timestamp = generate_timestamp()
    nonce = generate_nonce()
    signature_header_str = f"timestamp={timestamp}&nonce={nonce}"

    signature = calculate_signature(
        method="POST",
        path=PERSON_API_ENDPOINT,
        body=json.dumps(payload),
        timestamp=timestamp,
        nonce=nonce,
    )

    headers = build_signature_headers(signature, signature_header_str, API_KEY, nonce, timestamp)

    url = f"{api_base_url.rstrip('/')}{PERSON_API_ENDPOINT}"
    logger.info(f"请求URL: {url}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30, verify=False)
        response.raise_for_status()
        response_data = response.json()
        logger.debug(f"API 响应状态码: {response.status_code}")
        logger.debug(f"API 响应数据: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
    except requests.exceptions.RequestException as e:
        logger.error(f"请求 API 时发生网络错误: {e}")
        return {
            "success": False,
            "message": f"请求 API 时发生网络错误: {e}",
            "error_details": {"type": "network_error", "details": str(e)}
        }
    except json.JSONDecodeError as e:
        logger.error(f"解析 API 响应 JSON 失败: {e}")
        return {
            "success": False,
            "message": f"解析 API 响应 JSON 失败: {e}",
            "error_details": {"type": "json_decode_error", "details": str(e)}
        }

    try:
        code = str(response_data.get("code", "unknown")).strip()
        msg = response_data.get("msg", "未知错误")
        data = response_data.get("data", {})

        if code == "0":
            total = data.get("total", 0)
            returned_page_no = data.get("pageNo", page_number)
            returned_page_size = data.get("pageSize", page_size)
            raw_list = data.get("list", [])

            processed_list = []
            face_pic_urls = []

            for person in raw_list:
                cleaned = {k: (v.strip() if isinstance(v, str) else v) for k, v in person.items()}
                processed_person = {
                    "humanId": cleaned.get("humanId"),
                    "personLibId": cleaned.get("personLibId"),
                    "name": cleaned.get("name"),
                    "registerGender": cleaned.get("registerGender"),
                    "registerGenderName": cleaned.get("registerGenderName"),
                    "certificateType": cleaned.get("certificateType"),
                    "certificateTypeName": cleaned.get("certificateTypeName"),
                    "certificateNumber": cleaned.get("certificateNumber"),
                    "certificateNumberAsterisk": cleaned.get("certificateNumberAsterisk"),
                    "nativeCountyCode": cleaned.get("nativeCountyCode"),
                    "nativeCountyName": cleaned.get("nativeCountyName"),
                    "residenceCountyCode": cleaned.get("residenceCountyCode"),
                    "residenceCountyName": cleaned.get("residenceCountyName"),
                    "personLibName": cleaned.get("personLibName"),
                    "facePicture": cleaned.get("facePicture"),
                    "createTime": cleaned.get("createTime"),
                }
                processed_list.append(processed_person)
                face_pic_urls.append(cleaned["facePicture"])

            logger.info(f"成功获取到 {len(processed_list)} 条人员记录 (共 {total} 条)")
            return {
                "success": True,
                "message": "查询成功",
                "data": {
                    "total": total,
                    "page_number": returned_page_no,
                    "page_size": returned_page_size,
                    "persons": processed_list,
                    "face_pic_urls": face_pic_urls,
                }
            }
        else:
            logger.warning(f"API 返回错误: code={code}, msg={msg}")
            return {
                "success": False,
                "message": f"API 返回错误: {msg}",
                "error_details": {"code": code, "message": msg}
            }

    except Exception as e:
        logger.error(f"解析 API 响应数据时发生错误: {e}")
        return {
            "success": False,
            "message": f"解析 API 响应数据时发生错误: {e}",
            "error_details": {"type": "data_parsing_error", "details": str(e)}
        }


def dify_call_person_query(args):
    person_lib_id = args.get("person_lib_id")
    begin_time = args.get("begin_time")
    end_time = args.get("end_time")
    name = args.get("name")
    page_size = args.get("page_size")

    if not person_lib_id:
        raise ValueError("person_lib_id is required")

    result = queryPersonByAttrWithPage(
        person_lib_id=args.get("person_lib_id"),
        human_ids=args.get("human_ids"),
        name=args.get("name"),
        register_gender=args.get("register_gender"),
        certificate_type=args.get("certificate_type"),
        certificate_number=args.get("certificate_number"),
        native_county_code=args.get("native_county_code"),
        residence_county_code=args.get("residence_county_code"),
        begin_time=args.get("begin_time"),
        end_time=args.get("end_time"),
        page_number=args.get("page_number", 1),
        page_size=args.get("page_size", DEFAULT_PAGE_SIZE),
    )

    return result


# ----------------- 测试入口 -----------------
if __name__ == "__main__":
    os.environ["APP_SECRET_VALUE"] = "3aIZ1UAK1yAx4KrA7w0t"

    test_args = {
        "person_lib_id": "1",
        "certificate_number": "43108210090320081X",
        "begin_time": "2025-04-01",
    }

    result = dify_call_person_query(test_args)
    print(json.dumps(result, indent=2, ensure_ascii=False))
