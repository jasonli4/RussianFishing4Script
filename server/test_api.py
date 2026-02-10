"""
API测试脚本

用于测试卡密激活和验证接口
"""
import hashlib
import requests

# 配置
API_URL = "http://localhost:8000/verify_card"  # 如果在服务器外测试，改为服务器IP
API_SECRET = "Fishing@2026#Card"  # 需与config.py中一致


def generate_sign(params):
    """生成请求签名"""
    sorted_params = sorted(params.items(), key=lambda x: x[0])
    str_params = "".join([f"{k}{v}" for k, v in sorted_params]) + API_SECRET
    return hashlib.md5(str_params.encode()).hexdigest()


def test_activate(card_code, device_code):
    """测试激活接口"""
    print("\n===== 测试激活接口 =====")
    params = {
        "card_code": card_code,
        "device_code": device_code,
        "action": "activate"
    }
    params["sign"] = generate_sign(params.copy())

    print(f"请求参数：{params}")
    print(f"请求URL：{API_URL}")

    try:
        response = requests.post(API_URL, data=params, timeout=10)
        result = response.json()
        print(f"响应结果：{result}")
        return result
    except Exception as e:
        print(f"请求失败：{e}")
        return None


def test_check(card_code, device_code):
    """测试验证接口"""
    print("\n===== 测试验证接口 =====")
    params = {
        "card_code": card_code,
        "device_code": device_code,
        "action": "check"
    }
    params["sign"] = generate_sign(params.copy())

    print(f"请求参数：{params}")
    print(f"请求URL：{API_URL}")

    try:
        response = requests.post(API_URL, data=params, timeout=10)
        result = response.json()
        print(f"响应结果：{result}")
        return result
    except Exception as e:
        print(f"请求失败：{e}")
        return None


if __name__ == "__main__":
    import sys

    # 使用命令行参数或默认值
    if len(sys.argv) >= 3:
        card_code = sys.argv[1]
        device_code = sys.argv[2]
    else:
        print("使用方法：")
        print("  python3 test_api.py <卡密> <设备码>")
        print("\n示例：")
        print("  python3 test_api.py ABC1234567890123 my_device_code_123")
        print("\n使用默认测试值...")
        card_code = "TEST_CARD_12345678"
        device_code = "test_device_code_001"

    # 先测试激活
    activate_result = test_activate(card_code, device_code)

    # 如果激活成功，再测试验证
    if activate_result and activate_result.get("code") == 200:
        print("\n激活成功！现在测试验证接口...")
        test_check(card_code, device_code)
