@echo off
chcp 65001 >nul
echo ========================================
echo 城市片区功能适宜性分析系统 - 快速部署
echo ========================================
echo.

echo [1/4] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未检测到 Python，请先安装 Python 3.10+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo       Python 已安装

echo [2/4] 创建虚拟环境...
cd backend
if not exist venv (
    python -m venv venv
    echo       虚拟环境创建完成
) else (
    echo       虚拟环境已存在
)

echo [3/4] 激活环境并安装依赖...
call venv\Scripts\activate
pip install -r requirements.txt
if errorlevel 1 (
    echo 警告: 部分依赖安装失败，请检查错误信息
)

echo [4/4] 安装 GDAL...
pip install GDAL
if errorlevel 1 (
    echo 警告: GDAL 安装失败，请参考 DEPLOY.md 手动安装
)

echo.
echo ========================================
echo 部署完成！
echo ========================================
echo.
echo 使用方法: 双击 "启动系统.bat" 启动服务
echo.
pause