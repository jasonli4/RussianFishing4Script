# 卡密授权系统 - 部署说明

## 客户端（已完成）

客户端代码已集成到项目中，包括：
- `rf4s/auth/` - 授权模块
- `rf4s/config/auth_config.yaml` - 授权配置
- `main.py` - 已添加授权检查

依赖已安装：`pycryptodome`、`psutil`

## 服务器端部署步骤

### 1. 上传代码到服务器

将 `server/` 目录上传到宝塔服务器：

```bash
scp -r server/* root@your-server-ip:/www/wwwroot/fishing_card_api/
```

### 2. 创建数据库

在宝塔面板中：
1. 进入"数据库"菜单
2. 点击"添加数据库"
3. 填写信息：
   - 数据库名：`fishing_card`
   - 用户名：`fishing_user`
   - 密码：自定义（请记录）
   - 字符集：`utf8mb4`

### 3. 导入数据库表结构

通过SSH或宝塔终端执行：

```bash
cd /www/wwwroot/fishing_card_api
mysql -u fishing_user -p fishing_card < schema.sql
```

### 4. 修改配置文件

编辑 `/www/wwwroot/fishing_card_api/config.py`：

```python
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "fishing_user",
    "password": "你的数据库密码",  # 修改为实际密码
    "database": "fishing_card",
    "charset": "utf8mb4"
}

API_SECRET = "Fishing@2026#Card"  # 可自定义，需与客户端一致
API_PORT = 8000
```

### 5. 安装Python依赖

```bash
cd /www/wwwroot/fishing_card_api
pip3 install -r requirements.txt
```

### 6. 创建日志目录

```bash
mkdir -p /www/wwwroot/fishing_card_api/logs
```

### 7. 安装并使用PM2启动服务

#### 方式1：使用PM2（推荐）

**安装PM2**（如果没有安装）：
在宝塔面板中找到并安装 Node.js 版本管理器（推荐）
这是最符合宝塔面板使用习惯的方法：
正确查找入口
登录宝塔面板 → 左侧菜单「软件商店」
方法 A（直接搜索）：在搜索框输入「Node」或「Node 版本」（不要只输入 Node.js），应该能找到「Node.js 版本管理器」或「Node 版本管理器」
方法 B（分类查找）：进入软件商店后，点击顶部「运行环境」分类标签，在该分类下查找 Node 相关的版本管理工具
方法 C（更新软件列表）：如果仍未找到，点击软件商店右上角的「更新」按钮，刷新软件列表后重试
安装 Node.js 版本管理器
找到后点击「安装」，选择默认版本即可
安装完成后，点击「设置」进入管理器界面
安装 Node.js 主程序
在 Node.js 版本管理器中，选择16.x 或 18.x LTS 版本（推荐，兼容性最好，避免 20 + 版本）
点击「安装」，等待安装完成
安装后务必点击「设置为命令行版本」，让系统默认使用该版本
验证安装
打开宝塔面板的「终端」或本地 SSH 连接服务器
执行以下命令验证：
bash
运行
node -v  # 应输出Node.js版本号（如v16.20.2）
npm -v   # 应输出npm版本号（如8.19.4）

```bash
# 使用npm安装（如果没有npm，先安装Node.js）
npm install -g pm2

# 或者使用宝塔面板安装：
# 宝塔面板 -> 软件商店 -> 搜索"PM2管理器" -> 安装
```

**启动服务**：
```bash
cd /www/wwwroot/fishing_card_api
pm2 start ecosystem.config.json
pm2 save
pm2 startup  # 首次使用时执行，按提示操作
```

#### 方式2：使用nohup（无需PM2）

如果不想安装PM2，可以使用nohup启动：
```bash
cd /www/wwwroot/fishing_card_api
nohup python3 app.py > logs/app.log 2>&1 &
echo $! > logs/app.pid
```

**管理命令**：
- 查看日志：`tail -f logs/app.log`
- 停止服务：`kill $(cat logs/app.pid)`
- 重启服务：先停止再启动

#### 方式3：使用宝塔面板Python项目管理器

1. 宝塔面板 -> 软件商店 -> 搜索"Python项目管理器"
2. 安装后，添加项目：
   - 项目名称：fishing_card_api
   - 项目路径：/www/wwwroot/fishing_card_api
   - 启动文件：app.py
   - 端口：8000
3. 启动项目

查看状态：
```bash
pm2 status
pm2 logs fishing_card_api
```

### 8. 测试接口

使用Postman或curl测试：

```bash
curl -X POST http://your-server-ip:8000/verify_card \
  -d "card_code=TEST123&device_code=test123&action=activate&sign=xxx"
```

## 生成卡密

在服务器上运行卡密生成脚本：

```bash
cd /www/wwwroot/fishing_card_api
python3 generate_card.py
```

修改 `generate_card.py` 中的参数来生成不同类型和数量的卡密：

```python
# 示例：生成10个天卡
batch_generate_cards(card_type="1d", num=10)

# 生成其他类型：
# batch_generate_cards("2h", 5)    # 5个2小时卡
# batch_generate_cards("7d", 20)   # 20个周卡
# batch_generate_cards("30d", 10)  # 10个月卡
```

支持的卡密类型：
- `2h` - 2小时卡（7200秒）
- `1d` - 天卡（86400秒）
- `7d` - 周卡（604800秒）
- `15d` - 半月卡（1296000秒）
- `30d` - 月卡（2592000秒）
- `90d` - 季卡（7776000秒）
- `365d` - 年卡（31536000秒）

## 客户端配置

### 1. 配置授权信息

编辑 `rf4s/config/auth_config.yaml`：

```yaml
AUTH:
  API_URL: "http://your-server-ip:8000/verify_card"  # 修改为实际服务器地址
  API_SECRET: "Fishing@2026#Card"                     # 需与服务器一致
  AES_KEY: ""                                         # 首次运行自动生成
  AUTH_FILE: "auth_info.bin"
```

### 2. 首次运行

```bash
cd C:\1\RF4S1.0\RussianFishing4Script
python main.py
```

首次运行会提示：
1. 自动生成AES密钥
2. 显示设备码
3. 输入卡密
4. 激活成功后加密保存授权信息

### 3. 后续运行

每次运行会自动验证授权，显示剩余时长。

## 测试验证

### 功能测试

1. **首次激活测试**
   - 删除 `auth_info.bin` 文件
   - 运行脚本，输入有效卡密
   - 验证激活成功

2. **授权验证测试**
   - 正常运行脚本
   - 验证显示剩余时长

3. **错误场景测试**
   - 输入无效卡密
   - 输入已激活卡密
   - 卡密过期场景
   - 设备码不匹配场景

### 打包测试

使用Nuitka打包为EXE：

```bash
python -m nuitka --standalone --onefile --enable-plugin=pyside6 main.py
```

## 故障排查

### 客户端

1. **无法连接服务器**
   - 检查 `auth_config.yaml` 中的 `API_URL`
   - 确认服务器防火墙开放8000端口
   - 测试网络连通性：`ping your-server-ip`

2. **签名验证失败**
   - 确认客户端和服务器的 `API_SECRET` 一致

3. **授权文件损坏**
   - 删除 `auth_info.bin`，重新激活

### 服务器端

1. **PM2启动失败**
   - 检查日志：`pm2 logs fishing_card_api`
   - 检查Python版本：`python3 --version`（需3.7+）
   - 检查依赖安装：`pip3 list | grep flask pymysql`

2. **数据库连接失败**
   - 检查 `config.py` 中的数据库配置
   - 测试数据库连接：`mysql -u fishing_user -p fishing_card`

3. **接口无法访问**
   - 检查PM2状态：`pm2 status`
   - 检查端口监听：`netstat -tlnp | grep 8000`
   - 检查防火墙：宝塔面板 -> 安全 -> 放行端口8000

## 安全建议

1. **修改默认密钥**：修改 `API_SECRET` 为复杂随机字符串
2. **启用HTTPS**：使用Nginx反向代理 + Let's Encrypt证书
3. **IP白名单**：在Nginx配置中限制访问IP
4. **定期备份**：宝塔面板设置数据库自动备份
5. **监控日志**：定期检查 `logs/` 目录中的访问日志

## 后续优化

- [ ] 添加请求频率限制（Flask-Limiter）
- [ ] 实现Web管理界面
- [ ] 支持卡密续费功能
- [ ] 添加授权剩余时长提醒
- [ ] 实现多设备绑定管理
