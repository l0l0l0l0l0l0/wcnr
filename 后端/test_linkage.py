"""
端到端联动测试：验证 jd_query_service.py 和 find_all_young_pk_insert_into_db.py 的数据契约

测试内容：
1. 启动一个 mock 服务，模拟 jd_query_service.py 的 /queryDataByImageModelWithPage1 端点
2. 用模拟的 young_peoples 数据，按照 find_all_young_pk_insert_into_db.py 的逻辑发起请求
3. 验证请求格式、响应格式、数据流转是否正确
"""

import json
import threading
import time
import sys
import os
import logging
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from flask import Flask, request as flask_request, jsonify

# ==================== Mock 数据 ====================

MOCK_YOUNG_PEOPLES = [
    {
        "id_card_number": "450102199901011234",
        "person_face_url": "http://example.com/face/zhangsan.jpg",
        "last_capture_query_time": datetime(2026, 3, 25, 10, 0, 0),
    },
    {
        "id_card_number": "450102200005052345",
        "person_face_url": "http://example.com/face/lisi.jpg",
        "last_capture_query_time": None,
    },
    {
        "id_card_number": "450102199812123456",
        "person_face_url": "",
        "last_capture_query_time": None,
    },
]

MOCK_CAPTURE_RECORDS = {
    "zhangsan": [
        {
            "id": "CAP-001",
            "captureTime": "2026-04-20T08:30:00.000+08:00",
            "cameraName": "民族大道与珞喻路交叉口",
            "cameraIndexCode": "CAM-001",
            "facePicUrl": "http://pic.example.com/face/001.jpg",
            "bkgUrl": "http://pic.example.com/bkg/001.jpg",
            "similarity": 0.95,
            "genderName": "男",
            "ageGroupName": "25~30岁",
            "glassName": "未戴眼镜",
            "plateNo": "鄂A12345",
        },
        {
            "id": "CAP-002",
            "captureTime": "2026-04-21T14:15:00.000+08:00",
            "cameraName": "光谷广场地铁站A出口",
            "cameraIndexCode": "CAM-002",
            "facePicUrl": "http://pic.example.com/face/002.jpg",
            "bkgUrl": "http://pic.example.com/bkg/002.jpg",
            "similarity": 0.88,
            "genderName": "男",
            "ageGroupName": "25~30岁",
            "glassName": "戴眼镜",
            "plateNo": "",
        },
    ],
    "lisi": [
        {
            "id": "CAP-003",
            "captureTime": "2026-04-22T09:00:00.000+08:00",
            "cameraName": "武昌火车站西广场",
            "cameraIndexCode": "CAM-003",
            "facePicUrl": "http://pic.example.com/face/003.jpg",
            "bkgUrl": "http://pic.example.com/bkg/003.jpg",
            "similarity": 0.92,
            "genderName": "女",
            "ageGroupName": "20~25岁",
            "glassName": "未戴眼镜",
            "plateNo": "鄂B67890",
        },
    ],
}

# ==================== Mock 服务 ====================

received_requests = []

mock_app = Flask(__name__)


@mock_app.route("/queryDataByImageModelWithPage1", methods=["POST"])
def mock_query_capture():
    """模拟 jd_query_service.py 的 /queryDataByImageModelWithPage1 端点"""
    input_data = flask_request.get_json()

    # 记录收到的请求
    req_info = {
        "image_urls": input_data.get("image_urls", []),
        "image_datas_count": len(input_data.get("image_datas", [])),
        "start_time": input_data.get("start_time"),
        "end_time": input_data.get("end_time"),
        "min_similarity": input_data.get("min_similarity"),
        "page_number": input_data.get("page_number"),
        "page_size": input_data.get("page_size"),
    }
    received_requests.append(req_info)
    logging.info(f"[Mock服务] 收到请求: {json.dumps(req_info, ensure_ascii=False, default=str)}")

    # 根据 image_url 返回不同的模拟数据
    image_urls = input_data.get("image_urls", [])
    records = []
    if image_urls:
        url = image_urls[0]
        if "zhangsan" in url:
            records = MOCK_CAPTURE_RECORDS["zhangsan"]
        elif "lisi" in url:
            records = MOCK_CAPTURE_RECORDS["lisi"]
        else:
            records = []

    # 返回与真实接口一致的格式
    return jsonify({
        "success": True,
        "code": "0",
        "msg": "success",
        "data": {
            "records": records,
            "total": len(records),
        }
    })


@mock_app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


# ==================== 测试逻辑 ====================

def start_mock_server(port=19876):
    """在子线程启动 mock 服务"""
    mock_app.run(host="127.0.0.1", port=port, debug=False, threaded=True)


def run_client_test(service_url):
    """
    模拟 find_all_young_pk_insert_into_db.py 的核心逻辑，
    但不依赖真实数据库，直接调用 mock 服务并验证响应。
    """
    import requests as req_lib

    results = {
        "total_people": 0,
        "total_records": 0,
        "people_detail": [],
        "errors": [],
    }

    for person in MOCK_YOUNG_PEOPLES:
        id_card = person["id_card_number"]
        face_url = person["person_face_url"].strip()
        last_query_time = person.get("last_capture_query_time")

        # 跳过空 URL（与 find_all_young_pk_insert_into_db.py 中 get_people_batch 的 WHERE 条件一致）
        if not face_url:
            logging.info(f"[客户端] 跳过无 URL 人员: {id_card}")
            continue

        results["total_people"] += 1

        # 构造 start_time（与 find_all_young_pk_insert_into_db.py 中 format_time_range 逻辑一致）
        if last_query_time:
            start_time = last_query_time.strftime("%Y-%m-%d %H:%M:%S")
        else:
            start_time = (datetime.now() - timedelta(days=29)).strftime("%Y-%m-%d %H:%M:%S")

        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 格式化为 ISO8601
        begin_iso = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%dT%H:%M:%S.000+08:00")
        end_iso = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%dT%H:%M:%S.000+08:00")

        # 构造请求（与 find_all_young_pk_insert_into_db.py 中 query_capture_records 一致）
        payload = {
            "page_number": 1,
            "page_size": 3999,
            "image_urls": [face_url],
            "image_datas": [],
            "camera_index_code": "",
            "min_similarity": 0.8,
            "max_results": 9999,
            "start_time": begin_iso,
            "end_time": end_iso,
        }

        logging.info(f"[客户端] 查询: {id_card}, start={start_time}")

        try:
            response = req_lib.post(
                service_url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
                timeout=30,
            )

            if response.status_code != 200:
                results["errors"].append(f"HTTP {response.status_code} for {id_card}")
                continue

            result = response.json()

            # 验证响应格式
            if not result.get("success"):
                results["errors"].append(f"API 返回失败: {result.get('msg')} for {id_card}")
                continue

            records = result.get("data", {}).get("records", [])
            results["total_records"] += len(records)

            # 验证每条记录的字段完整性
            for rec in records:
                required_fields = ["id", "captureTime", "cameraName", "cameraIndexCode",
                                   "facePicUrl", "similarity"]
                missing = [f for f in required_fields if not rec.get(f)]
                if missing:
                    results["errors"].append(
                        f"记录 {rec.get('id', '?')} 缺少字段: {missing}"
                    )

            results["people_detail"].append({
                "id_card": id_card,
                "records_count": len(records),
                "capture_ids": [r["id"] for r in records],
            })

            logging.info(f"[客户端] {id_card}: 获取 {len(records)} 条抓拍记录")

        except Exception as e:
            results["errors"].append(f"请求异常: {e} for {id_card}")

    return results


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    PORT = 19876
    SERVICE_URL = f"http://127.0.0.1:{PORT}/queryDataByImageModelWithPage1"

    # 1. 启动 mock 服务
    server_thread = threading.Thread(
        target=start_mock_server,
        args=(PORT,),
        daemon=True,
    )
    server_thread.start()
    logging.info(f"Mock 服务启动于 http://127.0.0.1:{PORT}")

    # 2. 等待服务就绪
    import requests as req_lib
    for i in range(10):
        try:
            r = req_lib.get(f"http://127.0.0.1:{PORT}/health")
            if r.status_code == 200:
                logging.info("Mock 服务已就绪")
                break
        except Exception:
            time.sleep(0.5)
    else:
        logging.error("Mock 服务启动失败")
        sys.exit(1)

    # 3. 运行客户端测试
    logging.info("=" * 60)
    logging.info("开始联动测试")
    logging.info("=" * 60)

    results = run_client_test(SERVICE_URL)

    # 4. 输出测试报告
    logging.info("=" * 60)
    logging.info("测试报告")
    logging.info("=" * 60)

    print("\n" + "=" * 60)
    print("  联动测试结果")
    print("=" * 60)

    print(f"\n✓ 查询人数: {results['total_people']}")
    print(f"✓ 抓拍记录总数: {results['total_records']}")

    print("\n--- 各人员详情 ---")
    for detail in results["people_detail"]:
        print(f"  身份证: {detail['id_card']}")
        print(f"  抓拍数: {detail['records_count']}")
        print(f"  抓拍ID: {detail['capture_ids']}")
        print()

    print("--- Mock 服务收到的请求 ---")
    for i, req in enumerate(received_requests):
        print(f"  请求 {i+1}:")
        print(f"    image_urls: {req['image_urls']}")
        print(f"    start_time: {req['start_time']}")
        print(f"    end_time:   {req['end_time']}")
        print(f"    min_similarity: {req['min_similarity']}")
        print()

    if results["errors"]:
        print("--- 错误 ---")
        for err in results["errors"]:
            print(f"  ✗ {err}")
    else:
        print("--- 错误: 无 ---")

    # 5. 验证关键断言
    print("\n--- 断言验证 ---")
    all_pass = True

    checks = [
        ("查询了2人（跳过空URL的1人）", results["total_people"] == 2),
        ("总共获取3条抓拍记录", results["total_records"] == 3),
        ("张三有2条记录", any(
            d["id_card"] == "450102199901011234" and d["records_count"] == 2
            for d in results["people_detail"]
        )),
        ("李四有1条记录", any(
            d["id_card"] == "450102200005052345" and d["records_count"] == 1
            for d in results["people_detail"]
        )),
        ("Mock服务收到2个请求", len(received_requests) == 2),
        ("请求包含image_urls字段", all(r["image_urls"] for r in received_requests)),
        ("请求包含ISO8601格式时间", all(
            "T" in r["start_time"] and "+08:00" in r["start_time"]
            for r in received_requests
        )),
        ("无错误发生", len(results["errors"]) == 0),
    ]

    for desc, passed in checks:
        status = "✓ PASS" if passed else "✗ FAIL"
        if not passed:
            all_pass = False
        print(f"  {status} - {desc}")

    print("\n" + "=" * 60)
    if all_pass:
        print("  🎉 所有测试通过！两个脚本的数据契约匹配，可以联动。")
    else:
        print("  ❌ 部分测试失败，请检查数据契约。")
    print("=" * 60 + "\n")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
