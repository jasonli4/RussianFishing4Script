@echo off
REM =============================================
REM 俄罗斯钓鱼 4 脚本 - PyInstaller 打包脚本
REM =============================================

echo ============================================
echo 开始打包俄罗斯钓鱼 4 脚本...
echo ============================================
echo.

REM 检查 PyInstaller 是否安装
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [错误] PyInstaller 未安装，正在安装...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo [错误] PyInstaller 安装失败！
        pause
        exit /b 1
    )
)

echo [1/5] 清理旧的打包文件...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo [2/5] 开始打包（单文件模式）...
python -m PyInstaller ^
    --onefile ^
    --console ^
    --name "RF4S" ^
    --add-data "static;static" ^
    --add-data "rf4s/config/config.yaml;rf4s/config" ^
    --hidden-import "rf4s.auth" ^
    --hidden-import "rf4s.auth.device" ^
    --hidden-import "rf4s.auth.crypto" ^
    --hidden-import "rf4s.auth.client" ^
    --hidden-import "rf4s.auth.manager" ^
    --hidden-import "Crypto.Cipher" ^
    --hidden-import "Crypto.Util.Padding" ^
    --hidden-import "Cryptodome.Cipher" ^
    --hidden-import "Cryptodome.Util.Padding" ^
    --hidden-import "pyautogui" ^
    --hidden-import "pyscreeze" ^
    --hidden-import "psutil" ^
    --hidden-import "requests" ^
    --hidden-import "yaml" ^
    --hidden-import "yacs" ^
    --hidden-import "rich" ^
    --hidden-import "pynput" ^
    --hidden-import "keyboard" ^
    --hidden-import "cv2" ^
    --hidden-import "PIL" ^
    --hidden-import "matplotlib" ^
    --hidden-import "discord_webhook" ^
    --hidden-import "win32api" ^
    --hidden-import "win32con" ^
    --hidden-import "win32gui" ^
    main.py

if errorlevel 1 (
    echo [错误] 打包失败！
    pause
    exit /b 1
)

echo [3/5] 创建发布目录结构...
if exist "release" rmdir /s /q "release"
mkdir "release"

REM 复制 EXE
copy "dist\RF4S.exe" "release\" >nul

REM 创建必要的文件夹
mkdir "release\screenshots"
mkdir "release\logs"

REM 复制配置文件模板（首次运行时参考）
copy "rf4s\config\config.yaml" "release\config_template.yaml" >nul

echo [4/5] 创建说明文件...

REM 创建使用说明
echo 俄罗斯钓鱼 4 脚本 v0.9.0 > "release\使用说明.txt"
echo. >> "release\使用说明.txt"
echo ==================== 使用方法 ==================== >> "release\使用说明.txt"
echo 1. 双击运行 RF4S.exe >> "release\使用说明.txt"
echo 2. 首次运行会提示配置语言和鼠标设置 >> "release\使用说明.txt"
echo 3. 首次运行需要输入卡密激活（一机一卡） >> "release\使用说明.txt"
echo. >> "release\使用说明.txt"
echo ==================== 目录说明 ==================== >> "release\使用说明.txt"
echo - screenshots: 截图保存目录 >> "release\使用说明.txt"
echo - logs: 日志文件目录 >> "release\使用说明.txt"
echo - config.yaml: 配置文件（首次运行生成） >> "release\使用说明.txt"
echo - auth_config.yaml: 授权配置（自动生成，包含AES密钥） >> "release\使用说明.txt"
echo - auth_info.bin: 授权信息（激活后生成，AES加密） >> "release\使用说明.txt"
echo. >> "release\使用说明.txt"
echo ==================== 卡密激活说明 ==================== >> "release\使用说明.txt"
echo - 首次运行会显示设备码，需要购买卡密激活 >> "release\使用说明.txt"
echo - 激活后卡密与设备绑定，不可转移 >> "release\使用说明.txt"
echo - 每次启动会验证授权并显示剩余时长 >> "release\使用说明.txt"
echo - 如需更换设备，请联系客服解绑 >> "release\使用说明.txt"
echo. >> "release\使用说明.txt"
echo ==================== 常见问题 ==================== >> "release\使用说明.txt"
echo Q: 提示"无法定位游戏窗口"？ >> "release\使用说明.txt"
echo A: 请确保游戏已启动并完全显示在屏幕上 >> "release\使用说明.txt"
echo. >> "release\使用说明.txt"
echo Q: 提示"窗口大小不支持"？ >> "release\使用说明.txt"
echo A: 游戏窗口大小必须是 1600x900、1920x1080 或 2560x1440 >> "release\使用说明.txt"
echo. >> "release\使用说明.txt"
echo Q: 卡密激活失败？ >> "release\使用说明.txt"
echo A: 检查卡密是否正确、是否已被其他设备激活 >> "release\使用说明.txt"
echo. >> "release\使用说明.txt"

echo [5/5] 打包完成！
echo.
echo ============================================
echo 打包成功！文件位置: release\
echo ============================================
echo.
echo 发布目录内容:
dir /b "release"

echo.
echo ============================================
echo 发布包说明
echo ============================================
echo.
echo [重要] 首次运行流程：
echo 1. 用户运行 RF4S.exe
echo 2. 程序自动生成 auth_config.yaml（包含AES密钥）
echo 3. 显示设备码，提示输入卡密
echo 4. 验证卡密并激活，保存到 auth_info.bin（AES加密）
echo 5. 后续运行自动验证授权
echo.
echo [重要] 用户需要保留的文件：
echo - auth_config.yaml: 授权配置（包含AES密钥，不要删除）
echo - auth_info.bin: 授权信息（不要删除或分享）
echo.
echo [重要] 卡密服务器地址已内置：
echo - API_URL: http://120.55.246.246:8000/verify_card
echo - 用户可以通过修改 auth_config.yaml 更换服务器地址
echo.
echo 按任意键退出...
pause >nul
