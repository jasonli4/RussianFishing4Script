@echo off
REM =============================================
REM 清理打包临时文件
REM =============================================

echo 正在清理打包临时文件...

if exist "build" (
    echo 删除 build 目录...
    rmdir /s /q "build"
)

if exist "dist" (
    echo 删除 dist 目录...
    rmdir /s /q "dist"
)

if exist "release" (
    echo 删除 release 目录...
    rmdir /s /q "release"
)

if exist "*.spec" (
    echo 删除 .spec 文件...
    del /q "*.spec"
)

echo.
echo 清理完成！
echo.
pause
