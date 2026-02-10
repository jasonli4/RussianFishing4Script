"""
Flask卡密验证API接口

提供卡密激活和验证的REST API接口。
"""

from flask import Flask, request, jsonify
import pymysql
import datetime
import hashlib
from config import DB_CONFIG, API_SECRET, API_PORT

app = Flask(__name__)


def get_db_connection():
    """获取数据库连接"""
    conn = pymysql.connect(**DB_CONFIG)
    return conn


def verify_sign(params):
    """验证请求签名（防伪造）"""
    sign = params.pop("sign", "")
    sorted_params = sorted(params.items(), key=lambda x: x[0])
    str_params = "".join([f"{k}{v}" for k, v in sorted_params]) + API_SECRET
    md5_str = hashlib.md5(str_params.encode()).hexdigest()
    return md5_str == sign


@app.route("/verify_card", methods=["POST"])
def verify_card():
    """卡密激活/验证接口

    支持两种操作：
    - action=activate: 激活卡密（首次使用）
    - action=check: 验证卡密有效性（每次启动）

    请求参数：
    - card_code: 卡密字符串
    - device_code: 设备唯一码
    - action: activate或check
    - sign: MD5签名

    返回格式：
    {
        "code": 200,  # 200成功，其他为错误码
        "msg": "消息",
        "data": {}    # 成功时包含卡密信息
    }
    """
    try:
        # 1. 获取请求参数
        params = request.form.to_dict()
        card_code = params.get("card_code", "")
        device_code = params.get("device_code", "")
        action = params.get("action", "")

        # 2. 验证签名
        if not verify_sign(params):
            return jsonify({"code": 403, "msg": "签名验证失败", "data": None})

        # 3. 校验参数
        if not card_code or not device_code or action not in ["activate", "check"]:
            return jsonify({"code": 400, "msg": "参数缺失或错误", "data": None})

        # 4. 连接数据库查询卡密
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        cursor.execute("SELECT * FROM card_info WHERE card_code = %s", (card_code,))
        card_data = cursor.fetchone()

        if not card_data:
            cursor.close()
            conn.close()
            return jsonify({"code": 404, "msg": "卡密不存在", "data": None})

        # 5. 处理激活请求（action=activate）
        if action == "activate":
            # 检查是否已激活
            if card_data["is_activated"] == 1:
                cursor.close()
                conn.close()
                return jsonify({"code": 401, "msg": "卡密已激活，不可重复使用", "data": None})

            # 激活卡密：更新状态、绑定设备、计算过期时间
            activate_time = datetime.datetime.now()
            expire_time = activate_time + datetime.timedelta(seconds=card_data["valid_seconds"])
            cursor.execute("""
                UPDATE card_info
                SET is_activated=1, bind_device_code=%s, activate_time=%s, expire_time=%s
                WHERE card_code=%s
            """, (device_code, activate_time, expire_time, card_code))
            conn.commit()

            cursor.close()
            conn.close()
            return jsonify({
                "code": 200,
                "msg": "卡密激活成功",
                "data": {
                    "card_type": card_data["card_type"],
                    "activate_time": activate_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "expire_time": expire_time.strftime("%Y-%m-%d %H:%M:%S")
                }
            })

        # 6. 处理验证请求（action=check）
        elif action == "check":
            # 检查是否激活
            if card_data["is_activated"] == 0:
                cursor.close()
                conn.close()
                return jsonify({"code": 402, "msg": "卡密未激活", "data": None})

            # 检查设备是否匹配
            if card_data["bind_device_code"] != device_code:
                cursor.close()
                conn.close()
                return jsonify({"code": 405, "msg": "卡密绑定设备与当前设备不一致", "data": None})

            # 检查是否过期
            now = datetime.datetime.now()
            expire_time = card_data["expire_time"]
            if now > expire_time:
                cursor.close()
                conn.close()
                return jsonify({"code": 406, "msg": "卡密已过期", "data": None})

            # 验证通过
            cursor.close()
            conn.close()
            return jsonify({
                "code": 200,
                "msg": "卡密验证通过",
                "data": {
                    "card_type": card_data["card_type"],
                    "expire_time": expire_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "remaining_seconds": (expire_time - now).total_seconds()
                }
            })

    except Exception as e:
        return jsonify({"code": 500, "msg": f"服务器错误：{str(e)}", "data": None})


if __name__ == "__main__":
    # 启动Flask接口（允许外网访问）
    app.run(host="0.0.0.0", port=API_PORT, debug=False)
