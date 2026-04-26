# face_query_api.py
# 根据图片或模型数据查询人脸记录 (分页)
import query_api
import requests
import json
from datetime import datetime, timedelta
import logging
import urllib3

# 导入签名工具模块
from signature_utils import calculate_signature, generate_timestamp, generate_nonce, build_signature_headers

# 抑制 InsecureRequestWarning (如果使用 verify=False)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---- 配置部分 ----
# 请根据你的实际环境修改以下配置
API_BASE_URL = "https://71.196.10.25"
API_ENDPOINT = "/artemis/api/application/v1/face/queryDataByImageModelWithPage"
DEFAULT_PAGE_SIZE = 20
DEFAULT_TIME_RANGE_HOURS = 24

# ---- 配置结束 ----

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def query_face_records(
    image_urls: list = None,
    image_datas: list = None,
    model_data: str = None,
    camera_index_codes: str = None,
    min_similarity: float = 0.35,
    max_results: int = 8,
    start_time: str = None,
    end_time: str = None,
    page_number: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    sort_field: str = "similarity",
    sort_order: str = "desc",
    api_base_url: str = API_BASE_URL,
):
    if not image_urls and not image_datas:
        logger.error("imageUrls 或 imageDatas 至少提供一个。")
        return {"success": False, "message": "imageUrls 或 imageDatas 至少提供一个。"}

    # 时间处理
    now = datetime.now()
    tz_offset = "+08:00"
    if not end_time:
        end_time_dt = now
    else:
        try:
            end_time_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        except ValueError:
            logger.error(f"结束时间格式不正确: {end_time}")
            return {"success": False, "message": f"结束时间格式不正确: {end_time}"}

    if not start_time:
        start_time_dt = end_time_dt - timedelta(hours=DEFAULT_TIME_RANGE_HOURS)
    else:
        try:
            start_time_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        except ValueError:
            logger.error(f"开始时间格式不正确: {start_time}")
            return {"success": False, "message": f"开始时间格式不正确: {start_time}"}

    formatted_start_time = start_time_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + tz_offset
    formatted_end_time = end_time_dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + tz_offset

    # 构造请求体
    payload = {
        "pageNo": page_number,
        "pageSize": page_size,
        "sort": sort_field,
        "order": sort_order,
        "minSimilarity": min_similarity,
        "maxResults": max_results,
        "beginTime": formatted_start_time,
        "endTime": formatted_end_time,
        "imageInfo": {},
        "model": []
    }

    # 添加 imageInfo
    image_info = {}
    if image_urls:
        image_info["imageUrls"] = image_urls
    if image_datas:
        image_info["imageDatas"] = image_datas
    payload["imageInfo"] = image_info

    # 添加 model
    if model_data:
        payload["model"].append({"modelData": model_data})

    # 添加 cameraIndexCodes (可选)
    if camera_index_codes:
        payload["cameraIndexCodes"] = camera_index_codes

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

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30, verify=False)
        response.raise_for_status()
        response_data = response.json()
        logger.info(f"API 响应状态码: {response.status_code}")
        logger.debug(f"API 响应内容: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
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
    except Exception as e:
        logger.error(f"请求 API 时发生未知错误: {e}")
        return {
            "success": False,
            "message": f"请求 API 时发生未知错误: {e}",
            "error_details": {"type": "unknown_error", "details": str(e)}
        }

    # 解析响应
    try:
        code = response_data.get("code", "unknown").strip()  # 注意: 返回 code 可能有空格
        msg = response_data.get("msg", "未知错误")
        data = response_data.get("data", {})

        if code == "0":
            total = data.get("total", 0)
            returned_page_no = data.get("pageNo", page_number)
            returned_page_size = data.get("pageSize", page_size)
            raw_records = data.get("list", [])

            processed_records = []

            for record in raw_records:
                # 清理字段中的空格 (如 gender_, faceRect 等)
                processed_record = {
                    "id": record.get("id"),
                    "name": record.get("name"),
                    "gender": record.get("gender", "").strip(),
                    "genderName": record.get("genderName"),
                    "ageGroup": record.get("ageGroup", "").strip(),
                    "ageGroupName": record.get("ageGroupName"),
                    "glass": record.get("glass"),
                    "glassName": record.get("glassName"),
                    "cameraIndexCode": record.get("cameraIndexCode"),
                    "cameraName": record.get("cameraName"),
                    "certificateNumber": record.get("certificateNumber", "").strip(),
                    "faceRect": record.get("faceRect", "").strip(),
                    "linkFaceBodyId": record.get("linkFaceBodyId"),
                    "linkFaceVehicleId": record.get("linkFaceVehicleId"),
                    "plateNo": record.get("plateNo"),
                    "similarity": record.get("similarity"),
                    "captureTime": record.get("captureTime"),
                    "facePicUrl": record.get("facePicUrl", "").strip(),
                    "bkgUrl": record.get("bkgUrl")
                }
                processed_records.append(processed_record)

            logger.info(f"成功查询到 {len(processed_records)} 条人脸记录 (总 {total} 条)。")
            return {
                "success": True,
                "message": "查询成功",
                "data": {
                    "total": total,
                    "page_number": returned_page_no,
                    "page_size": returned_page_size,
                    "records": processed_records
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


def dify_call_allpic_by_url(args: dict):
    image_urls = args.get("image_urls") or []
    image_datas = args.get("image_datas")
    model_data = args.get("model_data")
    camera_index_codes = args.get("camera_index_codes")
    min_similarity = args.get("min_similarity", 0.35)
    max_results = args.get("max_results", 8)
    start_time = args.get("start_time")
    end_time = args.get("end_time")
    page_number = args.get("page_number", 1)
    page_size = args.get("page_size", DEFAULT_PAGE_SIZE)

    # 处理时间变量占位符
    now = datetime.now()
    if not end_time or end_time == "{{#end_time_variable}}":
        end_time = None
    if not start_time or start_time == "{{#start_time_variable}}":
        start_time = None

    result = query_face_records(
        image_urls=image_urls,
        image_datas=image_datas,
        model_data=model_data,
        camera_index_codes=camera_index_codes,
        min_similarity=min_similarity,
        max_results=max_results,
        start_time=start_time,
        end_time=end_time,
        page_number=page_number,
        page_size=page_size,
    )

    return result


if __name__ == "__main__":
    test_args = {
        "image_urls": [
            "http://71.196.10.24:6120/pic?-d9514e0019aa-c26-5p1e08-1158dd5e80e6711b9--0e016s1--idp2--4e887pw-mo41s--464233",
        ],
        "image_datas": [],
        # "model_data": "AAAAEQEggyAL+78YfVAsaH7/BH4/6BAAACAL=",
        "camera_index_codes": "-1",
        "min_similarity": 0.0,
        "max_results": 100,
        "start_time": "2020-03-15T00:00:00.000+08:00",
        "end_time": "2020-03-20T23:59:59.999+08:00",
        "page_number": 1,
        "page_size": 20,
        # "app_secret": "YOUR_REAL_APP_SECRET"  # 可通过环境变量设置
    }

    result = dify_call_allpic_by_url(test_args)
    print(json.dumps(result, indent=2, ensure_ascii=False))
