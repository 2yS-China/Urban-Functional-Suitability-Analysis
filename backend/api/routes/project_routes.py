"""
项目管理路由
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List
from api.project_manager import ProjectManager
from api.schemas import success_response, error_response
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
project_manager = ProjectManager()

# 请求模型
class CreateProjectRequest(BaseModel):
    """创建项目请求"""
    name: str = Field(..., min_length=1, max_length=100, description="项目名称")
    description: Optional[str] = Field(default="", max_length=500, description="项目描述")

class UpdateProjectRequest(BaseModel):
    """更新项目请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="项目名称")
    description: Optional[str] = Field(None, max_length=500, description="项目描述")

# 响应模型
class ProjectResponse(BaseModel):
    """项目响应"""
    id: str
    name: str
    description: str
    created_at: str
    updated_at: str
    status: str
    data_status: dict
    analysis_status: Optional[str]

@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_project(request: CreateProjectRequest):
    """
    创建新项目
    
    - **name**: 项目名称（必填）
    - **description**: 项目描述（可选）
    """
    try:
        project = project_manager.create_project(
            name=request.name,
            description=request.description
        )
        logger.info(f"项目创建成功: {project['id']}")
        return success_response(data=project, message="项目创建成功")
    
    except ValueError as e:
        logger.warning(f"项目创建失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"项目创建异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.get("/", response_model=dict)
async def list_projects(skip: int = 0, limit: int = 100):
    """
    列出所有项目
    
    - **skip**: 跳过数量（分页）
    - **limit**: 返回数量限制
    """
    try:
        projects = project_manager.list_projects(skip=skip, limit=limit)
        return success_response(
            data={
                "projects": projects,
                "total": len(projects),
                "skip": skip,
                "limit": limit
            },
            message="查询成功"
        )
    
    except Exception as e:
        logger.error(f"查询项目列表异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.get("/{project_id}", response_model=dict)
async def get_project(project_id: str):
    """
    获取项目详情
    
    - **project_id**: 项目ID
    """
    try:
        project = project_manager.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
        
        return success_response(data=project, message="查询成功")
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"查询项目详情异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.put("/{project_id}", response_model=dict)
async def update_project(project_id: str, request: UpdateProjectRequest):
    """
    更新项目信息
    
    - **project_id**: 项目ID
    - **name**: 新的项目名称（可选）
    - **description**: 新的项目描述（可选）
    """
    try:
        updates = {}
        if request.name is not None:
            updates["name"] = request.name
        if request.description is not None:
            updates["description"] = request.description
        
        if not updates:
            raise HTTPException(status_code=400, detail="没有提供更新内容")
        
        project = project_manager.update_project(project_id, updates)
        return success_response(data=project, message="项目更新成功")
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"更新项目异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.delete("/{project_id}", response_model=dict)
async def delete_project(project_id: str):
    """
    删除项目
    
    - **project_id**: 项目ID
    
    警告：此操作不可逆，将删除项目的所有数据
    """
    try:
        project_manager.delete_project(project_id)
        return success_response(message="项目删除成功")
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    except Exception as e:
        logger.error(f"删除项目异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")