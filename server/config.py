"""
服务器配置文件

包含数据库连接配置、API密钥和端口配置。
"""

# 数据库配置
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "fishing_user",
    "password": "your_database_password",  # 请修改为实际密码
    "database": "fishing_card",
    "charset": "utf8mb4"
}

# API安全密钥（需与客户端auth_config.yaml中的API_SECRET一致）
API_SECRET = "Fishing@2026#Card"

# 接口端口
API_PORT = 8000
