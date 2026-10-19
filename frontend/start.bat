@echo off
echo 启动前端开发服务器...
echo.
echo 前端服务: http://localhost:8080
echo API文档: http://localhost:8000/docs
echo.
echo 确保后端已启动: cd backend && uvicorn api.main:app --reload
echo.
python -m http.server 8080