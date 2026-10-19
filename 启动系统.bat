@echo off
echo ========================================
echo 城市片区功能适宜性分析系统 - 启动脚本
echo ========================================
echo.

echo [1/2] 启动后端API服务...
cd backend
start cmd /k "title Backend API && uvicorn api.main:app --reload --host 0.0.0.0 --port 8000"
echo     后端服务: http://localhost:8000
echo     API文档: http://localhost:8000/docs
echo.

timeout /t 3 /nobreak > nul

echo [2/2] 启动前端服务...
cd ..\frontend
start cmd /k "title Frontend Server && python -m http.server 8080"
echo     前端地址: http://localhost:8080
echo.

timeout /t 2 /nobreak > nul

echo ========================================
echo 系统启动完成！
echo ========================================
echo.
echo 正在打开浏览器...
start http://localhost:8080
echo.
echo 按任意键关闭此窗口...
pause > nul