"""
空间分析模块快速测试
使用少量网格快速验证功能
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import geopandas as gpd
import logging
from backend.spatial_analysis.feature_extractor import FeatureExtractor
from backend.spatial_analysis.suitability_evaluator import SuitabilityEvaluator
from backend.spatial_analysis.recommender import FunctionRecommender

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_quick():
    """快速测试"""
    logger.info("=" * 60)
    logger.info("空间分析模块快速测试")
    logger.info("=" * 60)
    
    # 加载数据
    logger.info("\n加载测试数据")
    data_dir = project_root / 'backend' / 'sample_data' / 'processed'
    
    grid = gpd.read_file(data_dir / 'grid_square_100m.geojson')
    poi = gpd.read_file(data_dir / 'poi_normalized.geojson')
    roads = gpd.read_file(data_dir / 'roads_normalized.geojson')
    
    # 只取前200个网格进行测试
    grid_sample = grid.head(200).copy()
    
    logger.info(f"测试网格数: {len(grid_sample)}")
    logger.info(f"POI数: {len(poi)}")
    logger.info(f"路网数: {len(roads)}")
    
    # 特征提取
    logger.info("\n特征提取")
    extractor = FeatureExtractor()
    features = extractor.extract_all_features(
        units=grid_sample,
        poi_data=poi,
        roads_data=roads
    )
    
    logger.info(f"提取特征维度: {len(features.columns) - 2}")
    logger.info(f"特征样例: {list(features.columns[:15])}")
    
    # 适宜性评价
    logger.info("\n适宜性评价")
    rules_file = project_root / 'backend' / 'spatial_analysis' / 'function_rules.yaml'
    evaluator = SuitabilityEvaluator(rules_config_path=str(rules_file))
    evaluation, details = evaluator.evaluate_all_functions(features)
    
    logger.info(f"评价功能类型: {evaluator.function_types}")
    for func_type in evaluator.function_types:
        score_col = f'score_{func_type}'
        if score_col in evaluation.columns:
            scores = evaluation[score_col]
            logger.info(f"  {func_type}: min={scores.min():.3f}, max={scores.max():.3f}, mean={scores.mean():.3f}")
    
    # 功能推荐
    logger.info("\n功能推荐")
    recommender = FunctionRecommender(
        mode='max_score',
        min_acceptable_score=0.4,
        spatial_coordination=True
    )
    result = recommender.recommend(evaluation, evaluator.function_types)
    
    # 保存结果
    logger.info("\n保存结果")
    output_dir = data_dir / 'analysis_results'
    output_dir.mkdir(exist_ok=True)
    
    result.to_file(output_dir / 'quick_test_result.geojson', driver='GeoJSON')
    logger.info(f"结果已保存: {output_dir / 'quick_test_result.geojson'}")
    
    # 示例单元
    logger.info("\n示例单元详情:")
    sample = result.nlargest(3, 'recommendation_score')
    for idx, unit in sample.iterrows():
        logger.info(f"\n单元 {unit['unit_id']}:")
        logger.info(f"  推荐: {unit['recommended_function']} (得分: {unit['recommendation_score']:.3f})")
        logger.info(f"  次选: {unit.get('second_choice', 'N/A')} (得分: {unit.get('second_score', 0):.3f})")
    
    logger.info("\n" + "=" * 60)
    logger.info("快速测试完成")
    logger.info("=" * 60)


if __name__ == '__main__':
    test_quick()