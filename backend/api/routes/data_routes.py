"""
数据上传路由
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status
from pathlib import Path
import logging
import geopandas as gpd
import json
import shutil
import zipfile
import tempfile
from typing import Optional

from api.project_manager import ProjectManager, ProjectConfig
from api.schemas import success_response, error_response

logger = logging.getLogger(__name__)

router = APIRouter()
project_manager = ProjectManager()

# 支持的文件格式
ALLOWED_EXTENSIONS = {
    "geojson": [".geojson", ".json"],
    "shapefile": [".zip"],  # Shapefile必须打包为ZIP
    "raster": [".tif", ".tiff"]
}

# 数据类型枚举
DATA_TYPES = [
    # 基础数据
    "boundary", "poi", "roads",
    # 地形地貌
    "dem",
    # 气候环境
    "precipitation",
    # 土地资源
    "landuse", "soil_type",
    # 水资源
    "water_bodies",
    # 经济指标
    "gdp_density",
    # 保护区约束
    "ecological_redline", "farmland_protection",
    # 建设现状
    "built_area",
    # 灾害风险
    "flood_risk", "geological_hazard",
    # 城市结构
    "city_center"
]

# 栅格数据类型
RASTER_DATA_TYPES = [
    "dem", "landuse", "precipitation", "soil_type",
    "gdp_density", "flood_risk", "geological_hazard"
]

# 矢量数据类型
VECTOR_DATA_TYPES = [
    "boundary", "poi", "roads", "water_bodies",
    "ecological_redline", "farmland_protection",
    "built_area", "city_center"
]

def validate_file_size(file: UploadFile, max_size_mb: int = ProjectConfig.MAX_UPLOAD_SIZE_MB):
    """验证文件大小"""
    file.file.seek(0, 2)  # 移动到文件末尾
    file_size = file.file.tell()
    file.file.seek(0)  # 重置到文件开头
    
    if file_size > max_size_mb * 1024 * 1024:
        raise ValueError(f"文件大小超过限制（{max_size_mb}MB）")
    
    return file_size

def validate_geodata(file_path: Path, data_type: str) -> dict:
    """
    验证地理数据
    
    Returns:
        dict: 包含数据统计信息
    """
    try:
        gdf = gpd.read_file(file_path)
        
        if gdf.empty:
            raise ValueError("数据为空")
        
        # 检查坐标系
        if gdf.crs is None:
            logger.warning(f"数据没有坐标系信息，将假定为WGS84")
            gdf = gdf.set_crs("EPSG:4326")
        
        # 检查几何类型
        geom_types = gdf.geom_type.unique().tolist()
        
        expected_geom_types = {
            "boundary": ["Polygon", "MultiPolygon"],
            "poi": ["Point", "MultiPoint"],
            "roads": ["LineString", "MultiLineString"],
            "water_bodies": ["Polygon", "MultiPolygon"],
            "ecological_redline": ["Polygon", "MultiPolygon"],
            "farmland_protection": ["Polygon", "MultiPolygon"],
            "built_area": ["Polygon", "MultiPolygon"],
            "city_center": ["Point", "MultiPoint"]
        }
        
        if data_type in expected_geom_types:
            valid_types = expected_geom_types[data_type]
            invalid_geoms = [gt for gt in geom_types if gt not in valid_types]
            if invalid_geoms:
                raise ValueError(f"{data_type}数据应为{valid_types}类型，发现{invalid_geoms}")
        
        # 返回统计信息
        stats = {
            "feature_count": len(gdf),
            "crs": str(gdf.crs),
            "geometry_types": geom_types,
            "bounds": gdf.total_bounds.tolist(),
            "columns": gdf.columns.tolist()
        }
        
        return stats
    
    except Exception as e:
        raise ValueError(f"数据验证失败: {str(e)}")

def extract_shapefile(zip_path: Path, extract_dir: Path) -> Path:
    """
    解压Shapefile ZIP包并返回.shp文件路径
    """
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    
    # 查找.shp文件
    shp_files = list(extract_dir.glob("**/*.shp"))
    if not shp_files:
        raise ValueError("ZIP包中未找到.shp文件")
    
    if len(shp_files) > 1:
        logger.warning(f"ZIP包中包含多个.shp文件，将使用第一个: {shp_files[0].name}")
    
    return shp_files[0]

@router.post("/projects/{project_id}/data/{data_type}", response_model=dict)
async def upload_data(
    project_id: str,
    data_type: str,
    file: UploadFile = File(...),
    description: Optional[str] = Form(None)
):
    """
    上传地理数据
    
    - **project_id**: 项目ID
    - **data_type**: 数据类型（boundary/poi/roads/dem/landuse）
    - **file**: 上传的文件（GeoJSON、Shapefile ZIP或TIF）
    - **description**: 数据描述（可选）
    """
    # 验证项目是否存在
    project = project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 验证数据类型
    if data_type not in DATA_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的数据类型。支持的类型: {DATA_TYPES}"
        )
    
    # 验证文件扩展名
    file_ext = Path(file.filename).suffix.lower()
    
    # 根据数据类型判断文件格式
    is_raster = data_type in RASTER_DATA_TYPES
    if is_raster:
        allowed_exts = ALLOWED_EXTENSIONS["raster"]
    else:
        allowed_exts = ALLOWED_EXTENSIONS["geojson"] + ALLOWED_EXTENSIONS["shapefile"]
    
    if file_ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式。支持的格式: {allowed_exts}"
        )
    
    try:
        # 验证文件大小
        file_size = validate_file_size(file)
        logger.info(f"上传文件大小: {file_size / 1024 / 1024:.2f}MB")
        
        # 获取项目原始数据目录
        raw_dir = project_manager.get_project_path(project_id, "raw")
        raw_dir.mkdir(exist_ok=True)
        
        # 保存上传文件
        upload_file_path = raw_dir / f"{data_type}_{file.filename}"
        with open(upload_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"文件保存成功: {upload_file_path}")
        
        # 验证数据（非栅格数据）
        stats = None
        if not is_raster:
            temp_dir = None
            try:
                # 如果是Shapefile，需要先解压
                if file_ext == ".zip":
                    temp_dir = Path(tempfile.mkdtemp())
                    data_file_path = extract_shapefile(upload_file_path, temp_dir)
                else:
                    data_file_path = upload_file_path
                
                # 验证数据
                stats = validate_geodata(data_file_path, data_type)
                logger.info(f"数据验证通过: {stats}")
            
            finally:
                # 清理临时目录
                if temp_dir and temp_dir.exists():
                    shutil.rmtree(temp_dir)
        else:
            # 栅格数据的基本验证
            try:
                import rasterio
                with rasterio.open(upload_file_path) as src:
                    stats = {
                        "width": src.width,
                        "height": src.height,
                        "crs": str(src.crs) if src.crs else None,
                        "bounds": src.bounds,
                        "count": src.count,
                        "dtype": str(src.dtypes[0])
                    }
                    logger.info(f"栅格数据验证通过: {stats}")
            except Exception as e:
                raise ValueError(f"栅格数据验证失败: {str(e)}")
        
        # 更新项目元数据
        updates = {
            "data_status": project.get("data_status", {})
        }
        updates["data_status"][data_type] = True
        project_manager.update_project(project_id, updates)
        
        return success_response(
            data={
                "file_name": file.filename,
                "file_size": file_size,
                "data_type": data_type,
                "stats": stats,
                "saved_path": str(upload_file_path.relative_to(project_manager.projects_dir))
            },
            message=f"{data_type}数据上传成功"
        )
    
    except ValueError as e:
        # 删除已上传的文件（如果存在）
        if upload_file_path.exists():
            upload_file_path.unlink()
        
        logger.warning(f"数据上传失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"数据上传异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.get("/projects/{project_id}/data/status", response_model=dict)
async def get_data_status(project_id: str):
    """
    查询项目数据状态
    
    - **project_id**: 项目ID
    """
    project = project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 获取原始数据目录
    raw_dir = project_manager.get_project_path(project_id, "raw")
    
    # 扫描已上传的文件
    uploaded_files = {}
    if raw_dir.exists():
        for file_path in raw_dir.iterdir():
            if file_path.is_file():
                # 从文件名提取数据类型
                for data_type in DATA_TYPES:
                    if file_path.name.startswith(f"{data_type}_"):
                        uploaded_files[data_type] = {
                            "file_name": file_path.name,
                            "file_size": file_path.stat().st_size,
                            "uploaded_at": file_path.stat().st_mtime
                        }
                        break
    
    return success_response(
        data={
            "project_id": project_id,
            "data_status": project.get("data_status", {}),
            "uploaded_files": uploaded_files
        },
        message="查询成功"
    )

@router.delete("/projects/{project_id}/data/{data_type}", response_model=dict)
async def delete_data(project_id: str, data_type: str):
    """
    删除已上传的数据
    
    - **project_id**: 项目ID
    - **data_type**: 数据类型
    """
    project = project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    if data_type not in DATA_TYPES:
        raise HTTPException(status_code=400, detail="不支持的数据类型")
    
    try:
        # 获取原始数据目录
        raw_dir = project_manager.get_project_path(project_id, "raw")
        
        # 查找并删除对应的文件
        deleted = False
        if raw_dir.exists():
            for file_path in raw_dir.iterdir():
                if file_path.name.startswith(f"{data_type}_"):
                    file_path.unlink()
                    deleted = True
                    logger.info(f"删除数据文件: {file_path}")
        
        if not deleted:
            raise HTTPException(status_code=404, detail="未找到该类型的数据文件")
        
        # 更新项目元数据
        updates = {
            "data_status": project.get("data_status", {})
        }
        updates["data_status"][data_type] = False
        project_manager.update_project(project_id, updates)
        
        return success_response(message=f"{data_type}数据删除成功")
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"删除数据异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.get("/projects/{project_id}/data/{data_type}/view", response_model=dict)
async def view_data(project_id: str, data_type: str):
    """
    获取已上传数据的GeoJSON用于地图可视化
    
    - **project_id**: 项目ID
    - **data_type**: 数据类型
    """
    project = project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    if data_type not in DATA_TYPES:
        raise HTTPException(status_code=400, detail="不支持的数据类型")
    
    # 检查数据是否已上传
    if not project.get("data_status", {}).get(data_type):
        raise HTTPException(status_code=404, detail=f"{data_type}数据尚未上传")
    
    try:
        # 优先查找标准化后的数据文件
        normalized_dir = project_manager.get_project_path(project_id, "normalized")
        raw_dir = project_manager.get_project_path(project_id, "raw")
        
        geojson_file = None
        
        # 先尝试从normalized目录查找
        if normalized_dir.exists():
            for file_path in normalized_dir.iterdir():
                if file_path.name.startswith(f"{data_type}_") and file_path.suffix in [".geojson", ".json"]:
                    geojson_file = file_path
                    break
        
        # 如果normalized目录没有，从raw目录查找并转换
        if not geojson_file and raw_dir.exists():
            for file_path in raw_dir.iterdir():
                if file_path.name.startswith(f"{data_type}_"):
                    # 读取并转换为GeoJSON
                    if file_path.suffix in [".geojson", ".json"]:
                        geojson_file = file_path
                        break
                    elif file_path.suffix == ".zip":
                        # Shapefile需要解压并读取
                        import tempfile
                        temp_dir = Path(tempfile.mkdtemp())
                        try:
                            shp_file = extract_shapefile(file_path, temp_dir)
                            gdf = gpd.read_file(shp_file)
                            geojson_data = json.loads(gdf.to_json())
                            
                            return success_response(
                                data={
                                    "type": "FeatureCollection",
                                    "features": geojson_data.get("features", []),
                                    "crs": geojson_data.get("crs"),
                                    "data_type": data_type
                                },
                                message="数据加载成功"
                            )
                        finally:
                            if temp_dir.exists():
                                shutil.rmtree(temp_dir)
        
        if not geojson_file or not geojson_file.exists():
            raise HTTPException(status_code=404, detail=f"未找到{data_type}的数据文件")
        
        # 读取GeoJSON
        with open(geojson_file, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)
        
        return success_response(
            data={
                "type": "FeatureCollection",
                "features": geojson_data.get("features", []),
                "crs": geojson_data.get("crs"),
                "data_type": data_type
            },
            message="数据加载成功"
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"加载数据用于可视化异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.get("/projects/{project_id}/results/view", response_model=dict)
async def view_results(project_id: str):
    """
    获取分析结果的GeoJSON用于地图可视化
    
    - **project_id**: 项目ID
    """
    project = project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 检查分析是否已完成
    if project.get("analysis_status") != "completed":
        raise HTTPException(status_code=404, detail="分析尚未完成")
    
    try:
        # 查找结果文件：以分析产出为准，兼容旧文件名
        results_dir = project_manager.get_project_path(project_id, "results")
        results_file = results_dir / "analysis_result.geojson"
        if not results_file.exists():
            results_file = results_dir / "suitability_results.geojson"
        
        if not results_file.exists():
            raise HTTPException(status_code=404, detail="未找到分析结果文件")
        
        # 读取GeoJSON
        with open(results_file, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)
        
        return success_response(
            data={
                "type": "FeatureCollection",
                "features": geojson_data.get("features", []),
                "crs": geojson_data.get("crs")
            },
            message="结果加载成功"
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"加载分析结果用于可视化异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")