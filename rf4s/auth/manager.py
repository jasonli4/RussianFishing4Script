"""授权管理器

提供高层的授权验证接口，处理首次激活、授权验证和本地授权文件管理。
"""

import json
import os
import sys
from pathlib import Path

import yaml
from yacs.config import CfgNode as CN

from rf4s import utils
from rf4s.auth.client import AuthClient
from rf4s.auth.crypto import aes_decrypt, aes_encrypt
from rf4s.auth.device import get_device_code

# 利用现有路径处理机制
INNER_ROOT = Path(__file__).resolve().parents[2]
if utils.is_compiled():
    OUTER_ROOT = Path(sys.executable).parent
else:
    OUTER_ROOT = INNER_ROOT


class AuthManager:
    """授权管理器

    处理授权验证的完整流程：
    - 首次激活：提示输入卡密，激活后加密保存
    - 验证授权：每次启动时验证卡密有效性
    - 本地存储：AES加密的授权文件
    """

    def __init__(self, cfg: CN):
        """初始化授权管理器

        Args:
            cfg: 配置节点，包含授权相关配置
        """
        self.cfg = cfg
        self.client = AuthClient(cfg)
        self.auth_file = OUTER_ROOT / cfg.AUTH.AUTH_FILE
        self._ensure_aes_key()

    def _ensure_aes_key(self):
        """确保AES密钥存在

        使用固定的内置密钥，不生成配置文件，避免暴露敏感信息。
        """
        # 使用固定的内置 AES 密钥（32字节）
        # 密钥长度必须正好是16、24或32字节
        aes_key = "12345678901234567890123456789012"  # 正好32字节

        self.aes_key = aes_key.encode()

    def _load_auth_info(self) -> dict:
        """解密本地授权信息

        Returns:
            dict: 授权信息字典，包含card_code、device_code、activate_time、expire_time
                  如果文件不存在或解密失败，返回None
        """
        if not self.auth_file.exists():
            return None

        try:
            with open(self.auth_file, "rb") as f:
                decrypted = aes_decrypt(f.read(), self.aes_key)
                return json.loads(decrypted.decode())
        except Exception:
            # 解密失败，删除损坏文件
            if self.auth_file.exists():
                os.remove(self.auth_file)
            return None

    def _save_auth_info(self, auth_info: dict) -> None:
        """加密保存授权信息

        Args:
            auth_info: 授权信息字典
        """
        encrypted = aes_encrypt(json.dumps(auth_info).encode(), self.aes_key)
        with open(self.auth_file, "wb") as f:
            f.write(encrypted)

    def _first_activate(self) -> bool:
        """首次激活流程

        提示用户输入卡密，向服务器发送激活请求，成功后加密保存授权信息。

        Returns:
            bool: 激活成功返回True，失败返回False
        """
        device_code = get_device_code()
        print("\n===== 卡密激活 =====")
        print(f"当前设备码：{device_code}（一机一卡，绑定后不可更换）")
        card_code = input("请输入卡密：").strip()

        result = self.client.activate_card(card_code, device_code)

        if result["code"] == 200:
            data = result["data"]
            print(f"激活成功！卡密类型：{data['card_type']}，过期时间：{data['expire_time']}")

            # 加密存储授权信息
            auth_info = {
                "card_code": card_code,
                "device_code": device_code,
                "activate_time": data["activate_time"],
                "expire_time": data["expire_time"]
            }
            self._save_auth_info(auth_info)
            return True
        else:
            print(f"激活失败：{result['msg']}")
            return False

    def check_auth(self) -> bool:
        """授权校验入口

        检查本地授权文件，如果不存在则进行首次激活。
        如果存在，则向服务器验证卡密有效性。

        Returns:
            bool: 授权验证通过返回True，失败会调用sys.exit()退出程序
        """
        # 首次激活
        if not self.auth_file.exists():
            if not self._first_activate():
                sys.exit(1)

        # 验证授权
        auth_info = self._load_auth_info()
        if not auth_info:
            print("授权信息损坏或不存在，请重新激活")
            if not self._first_activate():
                sys.exit(1)
            auth_info = self._load_auth_info()

        device_code = get_device_code()
        result = self.client.check_card(auth_info["card_code"], device_code)

        if result["code"] == 200:
            remaining_hours = result["data"]["remaining_seconds"] / 3600
            print(f"授权验证通过！剩余时长：{remaining_hours:.2f}小时")
            # 更新本地过期时间
            auth_info["expire_time"] = result["data"]["expire_time"]
            self._save_auth_info(auth_info)
            return True
        else:
            print(f"授权失效：{result['msg']}")
            if self.auth_file.exists():
                os.remove(self.auth_file)
            sys.exit(1)
