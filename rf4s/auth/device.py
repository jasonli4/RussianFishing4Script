"""设备唯一码生成模块

基于CPU序列号、硬盘信息和MAC地址生成设备唯一标识码。
"""

import hashlib
import os
import sys
import psutil


def get_device_code() -> str:
    """生成设备唯一码（CPU+硬盘+MAC -> MD5）

    通过收集硬件信息生成唯一标识码，实现一机一卡绑定。

    Returns:
        str: 32位MD5哈希值作为设备唯一码
    """
    try:
        # 获取CPU序列号
        cpu_serial = str(psutil.cpu_info().serial)

        # 获取硬盘信息
        disk_partitions = psutil.disk_partitions()
        disk_serial = disk_partitions[0].device if disk_partitions else "unknown"

        # 获取MAC地址（兼容中英文系统）
        mac = "00:00:00:00:00:00"
        for interface in psutil.net_if_addrs():
            # 优先查找有线网卡
            if "以太网" in interface or "Ethernet" in interface or "eth" in interface:
                mac = psutil.net_if_addrs()[interface][0].address
                break
            # 备选无线网卡
            if "Wi-Fi" in interface or "wifi" in interface:
                mac = psutil.net_if_addrs()[interface][0].address

        device_str = f"{cpu_serial}_{disk_serial}_{mac}"
    except Exception:
        # 后备方案：使用系统信息
        device_str = f"{os.name}_{sys.platform}_{os.getlogin()}"

    return hashlib.md5(device_str.encode()).hexdigest()
