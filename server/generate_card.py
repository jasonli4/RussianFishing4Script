"""
卡密批量生成脚本

用于批量生成不同时效的卡密并写入数据库。
"""

import pymysql
import random
import string
from config import DB_CONFIG

# 卡密类型映射（类型名称：有效秒数）
CARD_TYPE_MAP = {
    "2h": 7200,       # 2小时
    "1d": 86400,      # 1天
    "7d": 604800,     # 7天（周卡）
    "15d": 1296000,   # 15天（半月卡）
    "30d": 2592000,   # 30天（月卡）
    "90d": 7776000,   # 90天（季卡）
    "365d": 31536000  # 365天（年卡）
}


def generate_card_code(length=16):
    """生成随机卡密（大写字母+数字）

    Args:
        length: 卡密长度，默认16位

    Returns:
        str: 随机卡密字符串
    """
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def batch_generate_cards(card_type, num):
    """批量生成卡密并写入数据库

    Args:
        card_type: 卡密类型（2h/1d/7d/15d/30d/90d/365d）
        num: 生成数量
    """
    # 连接数据库
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    valid_seconds = CARD_TYPE_MAP.get(card_type, 0)
    if valid_seconds == 0:
        print("卡密类型错误！支持的类型：2h/1d/7d/15d/30d/90d/365d")
        return

    # 生成num个卡密并入库
    generated_cards = []
    for _ in range(num):
        card_code = generate_card_code()
        try:
            cursor.execute("""
                INSERT INTO card_info (card_code, card_type, valid_seconds)
                VALUES (%s, %s, %s)
            """, (card_code, card_type, valid_seconds))
            generated_cards.append(card_code)
        except pymysql.IntegrityError:
            # 卡密重复则重新生成
            card_code = generate_card_code()
            cursor.execute("""
                INSERT INTO card_info (card_code, card_type, valid_seconds)
                VALUES (%s, %s, %s)
            """, (card_code, card_type, valid_seconds))
            generated_cards.append(card_code)

    conn.commit()
    cursor.close()
    conn.close()

    print(f"成功生成{num}个{card_type}类型卡密：")
    for card in generated_cards:
        print(card)


if __name__ == "__main__":
    # 示例：生成10个天卡（1d）
    batch_generate_cards(card_type="1d", num=10)
    # 生成其他类型：batch_generate_cards("2h", 5) （5个2小时卡）
