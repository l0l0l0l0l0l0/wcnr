# face_compare_api.py
# 用人脸图片去查身份信息

import os
import requests
import json
from datetime import datetime
import logging
import urllib3
import time
import uuid

# 导入签名工具模块
from signature_utils import calculate_signature, generate_timestamp, generate_nonce, build_signature_headers

# 抑制 InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 配置部分 ---
API_BASE_URL = "https://71.196.10.25"
API_ENDPOINT = "/artemis/api/application/v2/face/queryByImageModelWithPage"

DEFAULT_PAGE_SIZE = 20
DEFAULT_MAX_RESULTS = 1000
DEFAULT_MIN_SIMILARITY = 0.85

# --- 认证信息配置(已移至 signature_utils 模块) ---

# --- 日志配置 ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def query_face_by_image(
    person_lib_id: str,
    image_url: str = None,
    image_data: str = None,
    model_data: str = None,
    image_rect: dict = None,
    page_number: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    max_results: int = DEFAULT_MAX_RESULTS,
    min_similarity: float = DEFAULT_MIN_SIMILARITY,
    api_base_url: str = API_BASE_URL,
):
    """
    通过图片进行人脸比对检索
    支持 image_url, image_data(Base64), model_data(特征值)三种方式传图
    """
    if not person_lib_id:
        logger.error("personLibId 是必需的。")
        return {"success": False, "message": "personLibId 是必需的。"}

    if not (image_url or image_data or model_data):
        logger.error("必须提供 image_url, image_data 或 model_data 之一。")
        return {"success": False, "message": "必须提供图片数据(image_url / image_data / model_data)之一。"}

    # 构造请求体
    payload = {
        "pageNo": page_number,
        "pageSize": page_size,
        "personLibId": person_lib_id,
        "maxResults": max_results,
        "minSimilarity": min_similarity,
    }

    if image_url:
        payload["imageUrl"] = image_url
    if image_data:
        payload["imageData"] = image_data
    if model_data:
        payload["modelData"] = model_data
    if image_rect:
        payload["imageRect"] = image_rect  # {x, y, width, height}

    logger.info(f"请求体: {json.dumps(payload, indent=2, ensure_ascii=False)}")

    # 签名参数 - 使用工具函数
    timestamp = generate_timestamp()
    nonce = generate_nonce()
    signature_headers_str = "x-ca-key,x-ca-nonce,x-ca-timestamp"

    signature = calculate_signature(
        method="POST",
        path=API_ENDPOINT,
        query="",
        body=json.dumps(payload),
        headers_to_sign=signature_headers_str,
        timestamp=timestamp,
        nonce=nonce,
        content_type="application/json"
    )

    # 请求头 - 使用工具函数构建
    headers = build_signature_headers(signature, signature_headers_str, timestamp, nonce)

    # 发送请求
    url = f"{api_base_url.rstrip('/')}{API_ENDPOINT}"
    print(f"DEBUG: Request URL: {url}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30, verify=False)
        response.raise_for_status()
        response.encoding = 'utf-8'
        response_data = response.json()
        logger.info(f"响应状态码: {response.status_code}")
        logger.debug(f"响应内容: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
    except requests.exceptions.RequestException as e:
        logger.error(f"网络请求失败: {e}")
        return {
            "success": False,
            "message": f"请求失败: {e}",
            "error_details": {"type": "network_error", "details": str(e)}
        }
    except json.JSONDecodeError as e:
        logger.error(f"JSON 解析失败: {e}")
        return {
            "success": False,
            "message": f"响应不是合法 JSON: {e}",
            "error_details": {"type": "json_decode_error", "details": str(e)}
        }

    # 解析响应
    try:
        code = str(response_data.get("code", "")).strip()
        msg = response_data.get("msg", "未知错误").strip()
        data = response_data.get("data", {})

        if code == "0":
            total = data.get("total", 0)
            list_data = data.get("list", [])
            processed_list = []
            face_urls = []

            for item in list_data:
                cleaned = {k.strip(): v for k, v in item.items() if v is not None}
                processed_item = {
                    "humanId": cleaned.get("humanId"),
                    "name": cleaned.get("name"),
                    "registerAge": cleaned.get("registerAge"),
                    "registerGender": cleaned.get("registerGender"),
                    "registerGenderName": cleaned.get("registerGenderName"),
                    "certificateType": cleaned.get("certificateType"),
                    "certificateTypeName": cleaned.get("certificateTypeName"),
                    "certificateNumber": cleaned.get("certificateNumber"),
                    "facePicUrl": cleaned.get("facePicUrl"),
                    "bkgUrl": cleaned.get("bkgUrl"),
                    "bornTime": cleaned.get("bornTime"),
                    "nativeCountyCode": cleaned.get("nativeCountyCode"),
                    "residenceCountyCode": cleaned.get("residenceCountyCode"),
                    "personLibId": cleaned.get("personLibId"),
                    "personLibName": cleaned.get("personLibName"),
                    "similarity": float(cleaned.get("similarity", 0.0)),
                    "createDate": cleaned.get("createDate"),
                }
                processed_list.append(processed_item)
                if cleaned.get("facePicUrl"):
                    face_urls.append(cleaned["facePicUrl"])

            logger.info(f"匹配到 {len(processed_list)} 个结果 (共 {total} 个)")
            return {
                "success": True,
                "message": "比对成功",
                "data": {
                    "total": total,
                    "page_number": data.get("pageNo", page_number),
                    "page_size": data.get("pageSize", page_size),
                    "results": processed_list,
                    "face_pic_urls": face_urls
                }
            }
        else:
            logger.warning(f"API 错误: code={code}, msg={msg}")
            return {
                "success": False,
                "message": f"API 错误: {msg}",
                "error_details": {"code": code, "message": msg}
            }

    except Exception as e:
        logger.error(f"解析响应失败: {e}")
        return {
            "success": False,
            "message": f"解析响应失败: {e}",
            "error_details": {"type": "parsing_error", "details": str(e)}
        }


def dify_call_face_compare(args: dict):
    """
    供 Dify 调用的入口函数
    """
    person_lib_id = args.get("person_lib_id")
    if not person_lib_id:
        raise ValueError("person_lib_id is required")

    image_url = args.get("image_url")
    image_data = args.get("image_data")
    model_data = args.get("model_data")
    image_rect = args.get("image_rect")  # dict: {x, y, width, height}

    result = query_face_by_image(
        person_lib_id=person_lib_id,
        image_url=image_url,
        image_data=image_data,
        model_data=model_data,
        image_rect=image_rect,
        page_number=args.get("page_number", 1),
        page_size=args.get("page_size", DEFAULT_PAGE_SIZE),
        max_results=args.get("max_results", DEFAULT_MAX_RESULTS),
        min_similarity=args.get("min_similarity", DEFAULT_MIN_SIMILARITY)
    )

    return result


# ============== 测试入口 ==============
if __name__ == "__main__":
    # 示例: 使用 imageUrl 进行比对
    test_args = {
        "person_lib_id": "951fe50e5f04c5101a492b5b07d0d23e",
        "image_url": "http://71.196.10.28:6081/pic?0914e0019aa-026-9p1ee0-11588d5e005e8711b0*-0d116s1*-ldp2t*-4d8t7pe*e011s-46423...",
        # "image_data": "AgAAADggEAAyAL+7BYFavsM7/BHa/n6BAACAA==",  # 可选
        # "model_data": ...,
        "image_rect": {
            "x": 0.1,
            "y": 0.1,
            "width": 0.51,
            "height": 0.51
        },
        "min_similarity": 0.85,
        "page_size": 20
    }

    # 设置 APP_SECRET (生产环境应通过环境变量)
    # os.environ['APP_SECRET_VALUE'] = '1b1UCj5yUvybK38vrkt'

    result = dify_call_face_compare(test_args)
    print(json.dumps(result, indent=2, ensure_ascii=False))
