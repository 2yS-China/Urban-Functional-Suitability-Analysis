"""
分析任务路由
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from pathlib import Path
import logging
import json
import uuid
from datetime import datetime
from enum import Enum

from api.project_manager import ProjectManager
from api.schemas import success_response
from api.analysis_worker import AnalysisWorker

logger = logging.getLogger(__name__)

router = APIRouter()
project_manager = ProjectManager()
analysis_worker = AnalysisWorker()

class GridMode(str, Enum):
    """网格模式"""
    SQUARE = "square"
    HEXAGON = "hexagon"
    PARCEL = "parcel"  # 使用地块

class AnalysisRequest(BaseModel):
    """分析请求参数"""
    grid_mode: GridMode = Field(default=GridMode.SQUARE, description="网格模式")
    grid_size: int = Field(default=100, ge=50, le=500, description="网格大小（米）")
    buffer_radius: int = Field(default=500, ge=100, le=2000, description="缓冲区半径（米）")
    include_terrain: bool = Field(default=False, description="是否包含地形分析")
    build_knowledge_graph: bool = Field(default=True, description="是否构建知识图谱")

class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    project_id: str
    status: TaskStatus
    progress: int  # 0-100
    message: str
    created_at: str
    updated_at: str
    result: Optional[Dict] = None
    error: Optional[str] = None

@router.post("/projects/{project_id}/analyze", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def start_analysis(
    project_id: str,
    request: AnalysisRequest,
    background_tasks: BackgroundTasks
):
    """
    启动分析任务
    
    - **project_id**: 项目ID
    - **grid_mode**: 网格模式（square/hexagon/parcel）
    - **grid_size**: 网格大小（米，50-500）
    - **buffer_radius**: 缓冲区半径（米，100-2000）
    - **include_terrain**: 是否包含地形分析
    - **build_knowledge_graph**: 是否构建知识图谱
    
    返回任务ID，可通过任务ID查询分析进度和结果
    """
    # 验证项目是否存在
    project = project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 检查必需数据是否已上传
    data_status = project.get("data_status", {})
    if not data_status.get("boundary"):
        raise HTTPException(status_code=400, detail="请先上传边界数据")
    
    if not data_status.get("poi"):
        raise HTTPException(status_code=400, detail="请先上传POI数据")
    
    if request.include_terrain and not data_status.get("dem"):
        raise HTTPException(status_code=400, detail="地形分析需要上传DEM数据")
    
    try:
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 创建任务元数据
        task_meta = {
            "task_id": task_id,
            "project_id": project_id,
            "status": TaskStatus.PENDING,
            "progress": 0,
            "message": "任务已创建，等待执行",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "params": request.dict(),
            "result": None,
            "error": None
        }
        
        # 保存任务元数据
        task_file = project_manager.get_project_path(project_id) / f"task_{task_id}.json"
        with open(task_file, "w", encoding="utf-8") as f:
            json.dump(task_meta, f, ensure_ascii=False, indent=2)
        
        # 更新项目分析状态
        project_manager.update_project(project_id, {
            "analysis_status": "running",
            "current_task_id": task_id
        })
        
        # 添加后台任务
        background_tasks.add_task(
            analysis_worker.run_analysis,
            task_id=task_id,
            project_id=project_id,
            params=request.dict()
        )
        
        logger.info(f"分析任务已创建: {task_id}, 项目: {project_id}")
        
        return success_response(
            data={
                "task_id": task_id,
                "project_id": project_id,
                "status": TaskStatus.PENDING,
                "message": "分析任务已启动"
            },
            message="分析任务创建成功"
        )
    
    except Exception as e:
        logger.error(f"创建分析任务异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.get("/tasks/{task_id}", response_model=dict)
async def get_task_status(task_id: str):
    """
    查询任务状态
    
    - **task_id**: 任务ID
    """
    try:
        # 查找任务文件（需要遍历所有项目）
        task_file = None
        for project_dir in project_manager.projects_dir.iterdir():
            if project_dir.is_dir():
                potential_task_file = project_dir / f"task_{task_id}.json"
                if potential_task_file.exists():
                    task_file = potential_task_file
                    break
        
        if not task_file:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 读取任务元数据
        with open(task_file, "r", encoding="utf-8") as f:
            task_meta = json.load(f)
        
        return success_response(data=task_meta, message="查询成功")
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"查询任务状态异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.get("/projects/{project_id}/results", response_model=dict)
async def get_analysis_results(project_id: str):
    """
    获取分析结果
    
    - **project_id**: 项目ID
    
    返回最新的分析结果，包括：
    - 网格单元GeoJSON
    - 统计汇总
    - 知识图谱（如果已构建）
    """
    # 验证项目是否存在
    project = project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 检查分析状态
    if not project.get("analysis_status") or project.get("analysis_status") == "pending":
        raise HTTPException(status_code=400, detail="项目尚未完成分析")
    
    try:
        results_dir = project_manager.get_project_path(project_id, "results")
        
        # 查找最新的结果文件
        result_file = results_dir / "analysis_result.geojson"
        if not result_file.exists():
            raise HTTPException(status_code=404, detail="分析结果文件不存在")
        
        # 读取GeoJSON结果
        with open(result_file, "r", encoding="utf-8") as f:
            geojson_data = json.load(f)
        
        # 读取统计数据
        stats_file = results_dir / "statistics.json"
        stats_data = None
        if stats_file.exists():
            with open(stats_file, "r", encoding="utf-8") as f:
                stats_data = json.load(f)
        
        # 读取知识图谱
        kg_file = results_dir / "knowledge_graph.json"
        kg_data = None
        if kg_file.exists():
            with open(kg_file, "r", encoding="utf-8") as f:
                kg_data = json.load(f)
        
        return success_response(
            data={
                "project_id": project_id,
                "geojson": geojson_data,
                "statistics": stats_data,
                "knowledge_graph": kg_data,
                "analysis_status": project.get("analysis_status")
            },
            message="查询成功"
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"获取分析结果异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.get("/projects/{project_id}/tasks", response_model=dict)
async def list_project_tasks(project_id: str):
    """
    列出项目的所有分析任务
    
    - **project_id**: 项目ID
    """
    # 验证项目是否存在
    project = project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    try:
        project_dir = project_manager.get_project_path(project_id)
        
        # 查找所有任务文件
        tasks = []
        for task_file in project_dir.glob("task_*.json"):
            with open(task_file, "r", encoding="utf-8") as f:
                task_meta = json.load(f)
                tasks.append(task_meta)
        
        # 按创建时间倒序排列
        tasks.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return success_response(
            data={
                "project_id": project_id,
                "tasks": tasks,
                "total": len(tasks)
            },
            message="查询成功"
        )
    
    except Exception as e:
        logger.error(f"列出任务异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")