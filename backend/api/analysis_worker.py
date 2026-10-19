"""
分析任务工作器
"""
import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict
import traceback
import geopandas as gpd
import pandas as pd

from api.project_manager import ProjectManager
from data_processor.normalizer import DataNormalizer
from data_processor.grid_generator import GridGenerator
from spatial_analysis.feature_extractor import FeatureExtractor
from spatial_analysis.suitability_evaluator import SuitabilityEvaluator
from spatial_analysis.recommender import FunctionRecommender
from kg.knowledge_graph_builder import KnowledgeGraphBuilder

logger = logging.getLogger(__name__)

class AnalysisWorker:
    """分析任务工作器"""
    
    def __init__(self):
        self.project_manager = ProjectManager()
    
    def run_analysis(self, task_id: str, project_id: str, params: Dict):
        """
        执行分析任务
        
        Args:
            task_id: 任务ID
            project_id: 项目ID
            params: 分析参数
        """
        logger.info(f"开始执行分析任务: {task_id}, 项目: {project_id}")
        
        try:
            # 更新任务状态
            self._update_task(task_id, project_id, "processing", 0, "初始化分析任务")
            
            # 获取项目路径
            project_dir = self.project_manager.get_project_path(project_id)
            raw_dir = project_dir / "raw"
            processed_dir = project_dir / "processed"
            results_dir = project_dir / "results"
            
            processed_dir.mkdir(exist_ok=True)
            results_dir.mkdir(exist_ok=True)
            
            # Step 1: 数据标准化 (10%)
            self._update_task(task_id, project_id, "processing", 10, "数据标准化")
            normalized_files = self._normalize_data(raw_dir, processed_dir, params)
            
            # Step 2: 网格生成 (25%)
            self._update_task(task_id, project_id, "processing", 25, "生成分析网格")
            grid_file = self._generate_grid(normalized_files, processed_dir, params)
            
            # Step 3: 特征提取 (50%)
            self._update_task(task_id, project_id, "processing", 50, "提取空间特征")
            features_file = self._extract_features(grid_file, normalized_files, processed_dir, params)
            
            # Step 4: 适宜性评价 (70%)
            self._update_task(task_id, project_id, "processing", 70, "适宜性评价")
            suitability_file = self._evaluate_suitability(features_file, processed_dir)
            
            # Step 5: 功能推荐 (85%)
            self._update_task(task_id, project_id, "processing", 85, "功能推荐")
            result_file = self._recommend_functions(suitability_file, results_dir)
            
            # Step 6: 统计分析
            self._update_task(task_id, project_id, "processing", 90, "生成统计数据")
            stats = self._generate_statistics(result_file, results_dir)
            
            # Step 7: 知识图谱构建 (可选)
            kg_file = None
            if params.get("build_knowledge_graph", True):
                self._update_task(task_id, project_id, "processing", 95, "构建知识图谱")
                kg_file = self._build_knowledge_graph(result_file, results_dir)
            
            # 任务完成
            result_data = {
                "result_file": str(result_file.relative_to(project_dir)),
                "statistics": stats,
                "knowledge_graph_file": str(kg_file.relative_to(project_dir)) if kg_file else None
            }
            
            self._update_task(
                task_id, project_id, "completed", 100,
                "分析完成", result=result_data
            )
            
            # 更新项目状态
            self.project_manager.update_project(project_id, {
                "analysis_status": "completed"
            })
            
            logger.info(f"分析任务完成: {task_id}")
        
        except Exception as e:
            error_msg = f"分析任务失败: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            
            self._update_task(
                task_id, project_id, "failed", -1,
                error_msg, error=traceback.format_exc()
            )
            
            # 更新项目状态
            self.project_manager.update_project(project_id, {
                "analysis_status": "failed"
            })
    
    def _normalize_data(self, raw_dir: Path, processed_dir: Path, params: Dict) -> Dict[str, Path]:
        """数据标准化"""
        normalizer = DataNormalizer()
        normalized_files = {}
        
        # 标准化边界数据
        boundary_file = self._find_data_file(raw_dir, "boundary")
        if boundary_file:
            gdf = normalizer.normalize_boundary(boundary_file, "default")
            output_path = processed_dir / "boundary_normalized.geojson"
            gdf.to_file(output_path, driver="GeoJSON")
            normalized_files["boundary"] = output_path
        
        # 标准化POI数据
        poi_file = self._find_data_file(raw_dir, "poi")
        if poi_file:
            gdf = normalizer.normalize_poi(poi_file, "default")
            output_path = processed_dir / "poi_normalized.geojson"
            gdf.to_file(output_path, driver="GeoJSON")
            normalized_files["poi"] = output_path
        
        # 标准化路网数据（可选）
        roads_file = self._find_data_file(raw_dir, "roads")
        if roads_file:
            gdf = normalizer.normalize_roads(roads_file, "default")
            output_path = processed_dir / "roads_normalized.geojson"
            gdf.to_file(output_path, driver="GeoJSON")
            normalized_files["roads"] = output_path
        
        # DEM数据（可选）
        if params.get("include_terrain", False):
            dem_file = self._find_data_file(raw_dir, "dem")
            if dem_file:
                normalized_files["dem"] = dem_file
        
        return normalized_files
    
    def _generate_grid(self, normalized_files: Dict[str, Path], processed_dir: Path, params: Dict) -> Path:
        """生成网格"""
        generator = GridGenerator()
        
        grid_mode = params.get("grid_mode", "square")
        grid_size = params.get("grid_size", 100)
        
        output_file = processed_dir / f"grid_{grid_mode}_{grid_size}m.geojson"
        
        if grid_mode == "parcel":
            # 使用地块模式（暂未实现）
            raise NotImplementedError("地块模式暂未实现")
        
        # 读取边界数据
        boundary_gdf = gpd.read_file(normalized_files["boundary"])
        
        # 生成网格
        grid_gdf = generator.generate_grid(
            boundary=boundary_gdf,
            grid_size=grid_size,
            mode=grid_mode,
            overlap_threshold=0.5
        )
        
        # 保存网格
        grid_gdf.to_file(output_file, driver="GeoJSON")
        
        return output_file
    
    def _extract_features(
        self,
        grid_file: Path,
        normalized_files: Dict[str, Path],
        processed_dir: Path,
        params: Dict
    ) -> Path:
        """提取空间特征"""
        extractor = FeatureExtractor()
        
        # 读取网格数据
        grid_gdf = gpd.read_file(grid_file)
        
        # 读取POI数据
        poi_gdf = gpd.read_file(normalized_files["poi"]) if "poi" in normalized_files else None
        
        # 读取路网数据
        roads_gdf = gpd.read_file(normalized_files["roads"]) if "roads" in normalized_files else None
        
        # 提取所有特征
        result_gdf = extractor.extract_all_features(
            units=grid_gdf,
            poi_data=poi_gdf,
            roads_data=roads_gdf,
            dem_path=str(normalized_files.get("dem")) if params.get("include_terrain") else None,
            water_path=str(normalized_files.get("water_bodies")) if "water_bodies" in normalized_files else None
        )
        
        # 保存结果
        output_file = processed_dir / "grid_with_features.geojson"
        result_gdf.to_file(output_file, driver="GeoJSON")
        
        return output_file
    
    def _evaluate_suitability(self, features_file: Path, processed_dir: Path) -> Path:
        """适宜性评价"""
        import geopandas as gpd
        
        evaluator = SuitabilityEvaluator()
        
        # 读取特征数据
        features = gpd.read_file(features_file)
        
        # 执行评价
        result_gdf, detailed_scores = evaluator.evaluate_all_functions(features)
        
        # 保存结果
        output_file = processed_dir / "grid_with_suitability.geojson"
        result_gdf.to_file(output_file, driver="GeoJSON")
        
        # 保存详细得分（可选）
        for func_type, details in detailed_scores.items():
            detail_file = processed_dir / f"suitability_{func_type}_details.geojson"
            details.to_file(detail_file, driver="GeoJSON")
        
        return output_file
    
    def _recommend_functions(self, suitability_file: Path, results_dir: Path) -> Path:
        """功能推荐"""
        import geopandas as gpd
        
        recommender = FunctionRecommender(
            mode='max_score',
            spatial_coordination=True
        )
        
        # 读取适宜性评价结果
        suitability_gdf = gpd.read_file(suitability_file)
        
        # 提取功能类型列表
        function_types = ['居住', '商业', '办公', '工业', '公共服务', '绿地休闲', '综合']
        
        # 执行推荐
        result_gdf = recommender.recommend(suitability_gdf, function_types)
        
        # 保存结果
        output_file = results_dir / "analysis_result.geojson"
        result_gdf.to_file(output_file, driver="GeoJSON")
        
        return output_file
    
    def _generate_statistics(self, result_file: Path, results_dir: Path) -> Dict:
        """生成统计数据"""
        import geopandas as gpd
        
        gdf = gpd.read_file(result_file)
        
        # 统计各功能的单元数量
        function_counts = gdf["recommended_function"].value_counts().to_dict()
        
        # 统计各功能的总面积
        function_areas = gdf.groupby("recommended_function")["geometry"].apply(
            lambda x: x.area.sum()
        ).to_dict()
        
        # 适宜性得分统计
        score_stats = {}
        score_columns = [col for col in gdf.columns if col.endswith("_score")]
        for col in score_columns:
            function_name = col.replace("_score", "")
            score_stats[function_name] = {
                "mean": float(gdf[col].mean()),
                "max": float(gdf[col].max()),
                "min": float(gdf[col].min()),
                "std": float(gdf[col].std())
            }
        
        stats = {
            "total_units": len(gdf),
            "function_counts": function_counts,
            "function_areas": function_areas,
            "score_statistics": score_stats,
            "generated_at": datetime.now().isoformat()
        }
        
        # 保存统计数据
        stats_file = results_dir / "statistics.json"
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        return stats
    
    def _build_knowledge_graph(self, result_file: Path, results_dir: Path) -> Path:
        """构建知识图谱"""
        import geopandas as gpd
        import yaml
        
        builder = KnowledgeGraphBuilder()
        
        # 读取分析结果
        result_gdf = gpd.read_file(result_file)
        
        # 提取特征字典
        features_dict = {}
        for idx, row in result_gdf.iterrows():
            unit_id = row.get('unit_id', idx)
            features = {}
            # 提取所有数值型特征
            for col in result_gdf.columns:
                if col not in ['geometry', 'unit_id', 'recommended_function', 
                               'recommendation_score', 'second_choice', 'second_score'] \
                   and not col.startswith('score_'):
                    try:
                        features[col] = float(row[col]) if pd.notna(row[col]) else 0.0
                    except (ValueError, TypeError):
                        pass
            features_dict[unit_id] = features
        
        # 提取适宜性得分矩阵
        suitability_matrix = {}
        function_types = ['居住', '商业', '办公', '工业', '公共服务', '绿地休闲', '综合']
        for idx, row in result_gdf.iterrows():
            unit_id = row.get('unit_id', idx)
            suitability_matrix[unit_id] = {}
            for func in function_types:
                score_col = f'score_{func}'
                if score_col in row:
                    suitability_matrix[unit_id][func] = float(row[score_col]) if pd.notna(row[score_col]) else 0.0
        
        # 提取推荐结果
        recommendations = {}
        for idx, row in result_gdf.iterrows():
            unit_id = row.get('unit_id', idx)
            recommendations[unit_id] = row.get('recommended_function', '待定')
        
        # 加载功能规则
        rules_file = Path(__file__).parent.parent / "spatial_analysis" / "function_rules.yaml"
        with open(rules_file, 'r', encoding='utf-8') as f:
            function_rules = yaml.safe_load(f)
        
        # 构建知识图谱
        kg = builder.build(
            units_gdf=result_gdf,
            features_dict=features_dict,
            suitability_matrix=suitability_matrix,
            recommendations=recommendations,
            function_rules=function_rules
        )
        
        # 保存知识图谱
        kg_file = results_dir / "knowledge_graph.json"
        kg.save_to_file(str(kg_file))
        
        return kg_file
    
    def _find_data_file(self, raw_dir: Path, data_type: str) -> Path:
        """查找数据文件"""
        if not raw_dir.exists():
            return None
        
        for file_path in raw_dir.iterdir():
            if file_path.name.startswith(f"{data_type}_"):
                return file_path
        
        return None
    
    def _update_task(
        self,
        task_id: str,
        project_id: str,
        status: str,
        progress: int,
        message: str,
        result: Dict = None,
        error: str = None
    ):
        """更新任务状态"""
        project_dir = self.project_manager.get_project_path(project_id)
        task_file = project_dir / f"task_{task_id}.json"
        
        # 读取现有任务数据
        with open(task_file, "r", encoding="utf-8") as f:
            task_meta = json.load(f)
        
        # 更新字段
        task_meta["status"] = status
        task_meta["progress"] = progress
        task_meta["message"] = message
        task_meta["updated_at"] = datetime.now().isoformat()
        
        if result:
            task_meta["result"] = result
        
        if error:
            task_meta["error"] = error
        
        # 保存
        with open(task_file, "w", encoding="utf-8") as f:
            json.dump(task_meta, f, ensure_ascii=False, indent=2)
        
        logger.info(f"任务状态更新: {task_id} - {status} ({progress}%) - {message}")