@echo off
echo ========================================
echo 城市片区功能适宜性分析系统 - 启动脚本
echo ========================================
echo.

echo [1/2] 启动后端API服务器...
start "Backend API" cmd /k "cd backend && uvicorn api.main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 3 /nobreak > nul

echo [2/2] 启动前端服务器...
start "Frontend Server" cmd /k "cd frontend && python -m http.server 8080"
timeout /t 2 /nobreak > nul

echo.
echo ========================================
echo 系统启动完成！
echo ========================================
echo.
echo 后端API: http://localhost:8000
echo API文档: http://localhost:8000/docs
echo 前端应用: http://localhost:8080
echo.
echo 按任意键打开浏览器...
pause > nul

start http://localhost:8080