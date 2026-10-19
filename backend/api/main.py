"""
FastAPI主应用
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="城市片区功能适宜性分析系统",
    description="基于GIS+AI的城市空间分析与策划决策工具",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境需要限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"全局异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "服务器内部错误",
            "detail": str(exc)
        }
    )

# 健康检查
@app.get("/")
async def root():
    """根路径，返回API信息"""
    return {
        "name": "城市片区功能适宜性分析系统",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "service": "urban-analysis-api"
    }

# 注册路由
from api.routes import project_routes, data_routes, analysis_routes, qa_routes

app.include_router(project_routes.router, prefix="/api/projects", tags=["项目管理"])
app.include_router(data_routes.router, prefix="/api", tags=["数据管理"])
app.include_router(analysis_routes.router, prefix="/api", tags=["分析任务"])
app.include_router(qa_routes.router, prefix="/api", tags=["知识问答"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )