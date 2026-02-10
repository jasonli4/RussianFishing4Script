"""授权网络请求客户端

负责与服务器进行卡密激活和验证的网络通信。
"""

import hashlib
import requests

from yacs.config import CfgNode as CN


class AuthClient:
    """授权网络客户端

    处理与授权服务器的所有通信，包括卡密激活和验证。
    """

    def __init__(self, cfg: CN):
        """初始化授权客户端

        Args:
            cfg: 配置节点，包含API_URL和API_SECRET
        """
        self.api_url = cfg.AUTH.API_URL
        self.api_secret = cfg.AUTH.API_SECRET

    def _generate_sign(self, params: dict) -> str:
        """生成请求签名（MD5）

        通过对参数排序后拼接密钥生成MD5签名，防止请求被伪造。

        Args:
            params: 请求参数字典

        Returns:
            str: MD5签名（32位十六进制字符串）
        """
        sorted_params = sorted(params.items(), key=lambda x: x[0])
        str_params = "".join([f"{k}{v}" for k, v in sorted_params]) + self.api_secret
        return hashlib.md5(str_params.encode()).hexdigest()

    def activate_card(self, card_code: str, device_code: str) -> dict:
        """激活卡密

        向服务器发送激活请求，首次使用卡密时调用。

        Args:
            card_code: 卡密字符串
            device_code: 设备唯一码

        Returns:
            dict: 服务器响应，包含code、msg和data字段
                - code: 200成功，其他为错误码
                - msg: 响应消息
                - data: 卡密类型、激活时间、过期时间等（成功时）
        """
        params = {
            "card_code": card_code,
            "device_code": device_code,
            "action": "activate"
        }
        params["sign"] = self._generate_sign(params.copy())

        try:
            response = requests.post(self.api_url, data=params, timeout=10)
            return response.json()
        except requests.exceptions.Timeout:
            return {"code": 504, "msg": "连接服务器超时，请检查网络", "data": None}
        except requests.exceptions.ConnectionError:
            return {"code": 503, "msg": "无法连接服务器", "data": None}
        except Exception as e:
            return {"code": 500, "msg": f"网络错误：{str(e)}", "data": None}

    def check_card(self, card_code: str, device_code: str) -> dict:
        """验证卡密有效性

        向服务器发送验证请求，每次启动脚本时调用。

        Args:
            card_code: 卡密字符串
            device_code: 设备唯一码

        Returns:
            dict: 服务器响应，包含code、msg和data字段
                - code: 200成功，其他为错误码
                - msg: 响应消息
                - data: 卡密类型、过期时间、剩余秒数等（成功时）
        """
        params = {
            "card_code": card_code,
            "device_code": device_code,
            "action": "check"
        }
        params["sign"] = self._generate_sign(params.copy())

        try:
            response = requests.post(self.api_url, data=params, timeout=10)
            return response.json()
        except requests.exceptions.Timeout:
            return {"code": 504, "msg": "连接服务器超时，请检查网络", "data": None}
        except requests.exceptions.ConnectionError:
            return {"code": 503, "msg": "无法连接服务器", "data": None}
        except Exception as e:
            return {"code": 500, "msg": f"网络错误：{str(e)}", "data": None}
