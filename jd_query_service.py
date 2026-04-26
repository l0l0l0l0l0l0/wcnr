from dotenv import load_dotenv
from flask import Flask, request, jsonify, Response
import os
import requests

from queryPersonByAttrWithPage import dify_call_person_query  # 导入根据人员身份查人脸
from queryByImageModelWithPage import dify_call_face_compare  # 导入根据人脸查身份
from queryDataByImageModelWithPage1 import dify_call_allpic_by_url  # 导入根据URL查抓拍
from choose_face_records import dify_call_insert_face_records  # 导入根据人脸查身份
from choose_people_together_insert_into_db import run_companion_clustering  # 导入同行人聚类方法
from find_drivers_insert_into_db import update_driver_status_from_json  # 导入同行人聚类方法
from operate_jddb_by_http import clear_and_insert_tmp_cameras
from other.get_to_message import send_message

load_dotenv()

app = Flask(__name__)

# 推荐方式：从环境变量读取
APP_SECRET = os.environ.get('APP_SECRET_VALUE')  # 请替换为你的环境变量名
if not APP_SECRET:
    raise ValueError("APP_SECRET environment variable not set!")


# 根据人员身份信息查询人脸
@app.route('/queryPersonByAttrWithPage', methods=['POST'])
def query_vehicle_images_endpoint():
    try:
        # 获取 Dify 数据
        input_data = request.get_json()
        if not input_data:
            return jsonify({"error": "No JSON data provided"}), 400

        # 从 input_data 中获取姓名或者身份证号
        name = input_data.get('name')
        certificate_number = input_data.get('certificate_number')
        print(input_data)
        if not name and not certificate_number:
            return jsonify({"error": "name or certificate_number is required"}), 400
        print("inputdata is :", input_data)

        result = dify_call_person_query(input_data)

        # 返回结果给 Dify
        return jsonify(result)

    except Exception as e:
        # 处理可能的错误
        print(f"Error in query_vehicle_images_endpoint: {e}")  # 记录错误日志
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


# 根据人脸查询身份信息
@app.route('/queryByImageModelWithPage', methods=['POST'])
def query_people_by_images():
    try:
        # 获取 Dify 发送的 JSON 数据
        input_data = request.get_json()
        if not input_data:
            return jsonify({"error": "No JSON data provided"}), 400

        # 从 input_data 中获取图片url
        image_url = input_data.get('image_url')
        print(image_url)
        image_data = input_data.get('image_data')
        model_data = input_data.get('model_data')
        if not image_url or image_data or model_data:
            return jsonify({"error": "image_url or image_data or model_data is required"}), 400
        print("inputdata is :", input_data)

        result = dify_call_face_compare(input_data)

        # 返回结果给 Dify
        return jsonify(result)

    except Exception as e:
        # 处理可能的错误
        print(f"Error in query_people_by_images: {e}")  # 记录错误日志
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


# 根据图片URL查询所有抓拍图片和信息
@app.route('/queryDataByImageModelWithPage1', methods=['POST'])
def query_allpic_by_url():
    try:
        # 获取 Dify 发送的 JSON 数据
        input_data = request.get_json()
        if not input_data:
            return jsonify({"error": "No JSON data provided"}), 400

        image_urls = input_data.get('image_urls')
        image_datas = input_data.get('image_datas')
        if len(image_urls) == 0 and len(image_datas) == 0:
            return jsonify({"error": "image_url or image_datas is required"}), 400

        result = dify_call_allpic_by_url(input_data)
        # 返回结果给 Dify
        return jsonify(result)

    except Exception as e:
        # 处理可能的错误
        print(f"Error in query_people_by_images: {e}")  # 记录错误日志
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


# 人脸图片转换成可展示的URL
@app.route('/proxy-pic')
def proxy_pic():
    url = request.args.get('url')
    print("proxy-pic:", url)
    if not url:
        return jsonify({"error": "url is required"}), 500

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "http://71.196.10.34/"
    }

    r = requests.get(url, headers=headers, stream=True)
    return Response(r.iter_content(1024), content_type=r.headers['Content-Type'])


# 将抓拍信息插入或更新到数据库
@app.route('/insertFaceRecordsIntoDb', methods=['POST'])
def insert_face_records():
    try:
        # 获取 Dify 发送的 JSON 数据
        input_data = request.get_json()
        if not input_data:
            return jsonify({"error": "No JSON data provided"}), 400
        cert_no = request.args.get('certificateNumber')

        if not cert_no:
            return jsonify({"error": "缺少 certificateNumber 参数"}), 400
        print("inputdata is :", input_data)
        result = dify_call_insert_face_records(input_data, cert_no)

        # 返回结果给 Dify
        return jsonify(result)

    except Exception as e:
        # 处理可能的错误
        print(f"Error in insert_face_records: {e}")  # 记录错误日志
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


# 同行人聚类方法
@app.route('/cluster', methods=['POST'])
def cluster_api():
    """
    Dify平台调用的API接口
    请求体示例：
    {
        "start_time": "2026-02-01 00:00:00",
        "end_time": "2026-02-27 23:59:59",
        "time_window_up": 3600,
        "time_window_down": 0,
        "cameras_type": 30
    }
    """
    try:
        # 获取请求参数
        data = request.json
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        time_window_up = data.get('time_window_up')
        time_window_down = data.get('time_window_down')
        cameras_type = data.get('cameras_type')

        # 调用聚类处理函数
        result = run_companion_clustering(
            start_time, end_time, time_window_up, time_window_down, cameras_type
        )
        print("聚类接口结束并成功返回+++++++++")
        # 返回JSON响应
        return jsonify(result)

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'API调用失败',
            'data': {}
        }), 500


# 判断是否为同机
@app.route('/judgeDrivers', methods=['POST'])
def judge_drivers():
    """
    Dify平台调用的API接口
    接收JSON数据格式：
    {
        "all_driver": [
            {"is_driver1": 0, "cr_id1": 30492},
            {"is_driver1": 1, "cr_id1": 30499}
        ]
    }
    """
    try:
        # 获取请求参数
        data = request.json

        # 调用同机推理更新函数
        result = update_driver_status_from_json(data)

        # 返回JSON响应
        return jsonify(result)

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'API调用失败',
            'updated_count': 0
        }), 500


# 直接调用清空并插入tmp_cameras的接口
@app.route('/updateTmpCameras', methods=['POST'])
def update_tmp_cameras():
    """
    直接调用清空并插入tmp_cameras表的接口
    """
    try:
        result = clear_and_insert_tmp_cameras()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'更新tmp_cameras表失败: {str(e)}',
            'data': {}
        }), 500


# 发送八桂信息到指定人员
@app.route('/send_message_by_bagui', methods=['POST'])
def send_message_by_bagui():
    """
    Dify平台调用的API接口
    接收JSON数据格式：
    {
        "touser": "452482199302200010"
        "content": "查询近一周的数据"
    }
    """
    try:
        # 获取请求参数
        data = request.json
        if data:
            touser = data.get('touser')
            content = data.get('content')
            result = send_message(touser, content)
            print('已经返回结果----------')
            return jsonify(result)
        else:
            return jsonify({
                'status': 'error',
                'message': '传入数据不能为空',
            }), 405
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': '接口数据处理失败',
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5020, debug=False, threaded=True)
