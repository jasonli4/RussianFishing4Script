@echo off
REM =============================================
REM 一键打包、测试和发布
REM =============================================

echo ============================================
echo 俄罗斯钓鱼 4 脚本 - 自动打包发布工具
echo ============================================
echo.

REM 检查 PyInstaller
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [1/5] 安装 PyInstaller...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo [错误] PyInstaller 安装失败！
        pause
        exit /b 1
    )
) else (
    echo [1/5] PyInstaller 已安装
)

REM 清理旧文件
echo [2/5] 清理旧的打包文件...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "release" rmdir /s /q "release"

REM 打包
echo [3/5] 开始打包（这可能需要几分钟）...
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
    --hidden-import "PIL.Image" ^
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

REM 创建发布目录
echo [4/5] 创建发布目录...
mkdir "release"
copy "dist\RF4S.exe" "release\" >nul
mkdir "release\screenshots"
mkdir "release\logs"

REM 创建说明文件
echo 俄罗斯钓鱼 4 脚本 v0.9.0 - 卡密授权版 > "release\使用说明.txt"
echo ============================================ >> "release\使用说明.txt"
echo. >> "release\使用说明.txt"
echo 使用说明 >> "release\使用说明.txt"
echo ------- >> "release\使用说明.txt"
echo 1. 双击运行 RF4S.exe >> "release\使用说明.txt"
echo 2. 首次运行会提示配置： >> "release\使用说明.txt"
echo    - 选择游戏语言（en/ru） >> "release\使用说明.txt"
echo    - 是否启用鼠标点击锁定 >> "release\使用说明.txt"
echo 3. 首次运行需要输入卡密激活 >> "release\使用说明.txt"
echo 4. 授权信息会自动保存 >> "release\使用说明.txt"
echo. >> "release\使用说明.txt"
echo 目录说明 >> "release\使用说明.txt"
echo ------- >> "release\使用说明.txt"
echo - screenshots: 截图自动保存目录 >> "release\使用说明.txt"
echo - logs: 程序运行日志 >> "release\使用说明.txt"
echo - config.yaml: 配置文件（首次运行生成） >> "release\使用说明.txt"
echo - auth_info.bin: 授权信息（激活后生成，请勿删除） >> "release\使用说明.txt"
echo. >> "release\使用说明.txt"
echo 注意事项 >> "release\使用说明.txt"
echo ------- >> "release\使用说明.txt"
echo - 本程序需要卡密授权才能使用 >> "release\使用说明.txt"
echo - 一机一卡，绑定后不可更换 >> "release\使用说明.txt"
echo - 请妥善保管授权文件 >> "release\使用说明.txt"
echo - 不要删除或分享 auth_info.bin 文件 >> "release\使用说明.txt"
echo. >> "release\使用说明.txt"

REM 完成
echo [5/5] 打包完成！
echo.
echo ============================================
echo 发布包已准备就绪！
echo ============================================
echo.
echo 发布位置: release\
echo.
echo 发布内容:
dir /b "release"
echo.
echo 文件大小:
for %%A in ("release\RF4S.exe") do echo RF4S.exe: %%~zA 字节 ^(约 %%~zA:1024:1024 MB^)
echo.
echo ============================================
echo.
echo 按任意键进行快速测试，或关闭窗口退出...
pause >nul

REM 快速测试
echo.
echo [快速测试] 启动程序...
cd release
start RF4S.exe

echo.
echo 程序已启动，请检查：
echo 1. 是否正常显示界面
echo 2. 首次运行会提示配置
echo 3. 需要输入卡密激活
echo.
echo 如果测试正常，按任意键关闭测试窗口...
pause >nul

REM 关闭测试程序
taskkill /f /im RF4S.exe >nul 2>&1

echo.
echo 测试完成！release\ 目录可以发布了。
echo.
pause
