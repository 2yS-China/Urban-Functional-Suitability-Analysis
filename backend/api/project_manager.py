"""
项目管理服务
"""
import json
import shutil
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ProjectConfig:
    """项目配置"""
    # 数据根目录
    DATA_ROOT = Path(__file__).parent.parent / "data"
    PROJECTS_DIR = DATA_ROOT / "projects"
    
    # 单个项目最大大小（MB）
    MAX_PROJECT_SIZE_MB = 500
    
    # 文件大小限制（MB）
    MAX_UPLOAD_SIZE_MB = 50

class ProjectManager:
    """项目管理器"""
    
    def __init__(self):
        self.projects_dir = ProjectConfig.PROJECTS_DIR
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"项目管理器初始化，数据目录: {self.projects_dir}")
    
    def create_project(self, name: str, description: str = "") -> Dict:
        """创建新项目"""
        project_id = self._generate_project_id(name)
        project_dir = self.projects_dir / project_id
        
        if project_dir.exists():
            raise ValueError(f"项目已存在: {project_id}")
        
        # 创建项目目录结构
        project_dir.mkdir(parents=True)
        (project_dir / "raw").mkdir()  # 原始上传数据
        (project_dir / "processed").mkdir()  # 处理后的数据
        (project_dir / "results").mkdir()  # 分析结果
        (project_dir / "exports").mkdir()  # 导出文件
        
        # 创建项目元数据
        metadata = {
            "id": project_id,
            "name": name,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "created",
            "data_status": {
                "boundary": False,
                "poi": False,
                "roads": False
            },
            "analysis_status": None
        }
        
        self._save_metadata(project_id, metadata)
        logger.info(f"项目创建成功: {project_id}")
        return metadata
    
    def list_projects(self, skip: int = 0, limit: int = 100) -> List[Dict]:
        """列出所有项目"""
        projects = []
        for project_dir in self.projects_dir.iterdir():
            if project_dir.is_dir():
                try:
                    metadata = self._load_metadata(project_dir.name)
                    projects.append(metadata)
                except Exception as e:
                    logger.warning(f"加载项目元数据失败: {project_dir.name}, {e}")
        
        # 按创建时间倒序排列
        projects.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return projects[skip:skip + limit]
    
    def get_project(self, project_id: str) -> Optional[Dict]:
        """获取项目详情"""
        try:
            return self._load_metadata(project_id)
        except FileNotFoundError:
            return None
    
    def update_project(self, project_id: str, updates: Dict) -> Dict:
        """更新项目信息"""
        metadata = self._load_metadata(project_id)
        
        # 允许更新的字段
        allowed_fields = ["name", "description", "data_status", "analysis_status"]
        for field in allowed_fields:
            if field in updates:
                metadata[field] = updates[field]
        
        metadata["updated_at"] = datetime.now().isoformat()
        self._save_metadata(project_id, metadata)
        logger.info(f"项目更新成功: {project_id}")
        return metadata
    
    def delete_project(self, project_id: str) -> bool:
        """删除项目"""
        project_dir = self.projects_dir / project_id
        if not project_dir.exists():
            raise FileNotFoundError(f"项目不存在: {project_id}")
        
        shutil.rmtree(project_dir)
        logger.info(f"项目删除成功: {project_id}")
        return True
    
    def get_project_path(self, project_id: str, subdir: str = "") -> Path:
        """获取项目路径"""
        project_dir = self.projects_dir / project_id
        if not project_dir.exists():
            raise FileNotFoundError(f"项目不存在: {project_id}")
        
        if subdir:
            return project_dir / subdir
        return project_dir
    
    def _generate_project_id(self, name: str) -> str:
        """生成项目ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 简化名称，去除特殊字符
        safe_name = "".join(c for c in name if c.isalnum() or c in ("-", "_"))[:20]
        return f"{safe_name}_{timestamp}"
    
    def _load_metadata(self, project_id: str) -> Dict:
        """加载项目元数据"""
        metadata_file = self.projects_dir / project_id / "metadata.json"
        if not metadata_file.exists():
            raise FileNotFoundError(f"项目元数据不存在: {project_id}")
        
        with open(metadata_file, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _save_metadata(self, project_id: str, metadata: Dict):
        """保存项目元数据"""
        metadata_file = self.projects_dir / project_id / "metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)