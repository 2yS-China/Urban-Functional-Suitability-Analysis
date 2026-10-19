"""
空间分析模块测试脚本
测试特征提取、适宜性评价、功能推荐的完整流程
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import geopandas as gpd
import logging
from backend.spatial_analysis.feature_extractor import FeatureExtractor
from backend.spatial_analysis.suitability_evaluator import SuitabilityEvaluator
from backend.spatial_analysis.recommender import FunctionRecommender

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_full_spatial_analysis():
    """测试完整的空间分析流程"""
    logger.info("=" * 60)
    logger.info("开始空间分析模块完整流程测试")
    logger.info("=" * 60)
    
    # 1. 加载测试数据
    logger.info("\n步骤 1: 加载测试数据")
    data_dir = project_root / 'backend' / 'sample_data' / 'processed'
    
    grid_file = data_dir / 'grid_square_100m.geojson'
    poi_file = data_dir / 'poi_normalized.geojson'
    road_file = data_dir / 'roads_normalized.geojson'
    
    if not grid_file.exists():
        logger.error(f"网格文件不存在: {grid_file}")
        logger.info("请先运行 test_data_processing.py 生成测试数据")
        return
    
    grid = gpd.read_file(grid_file)
    poi = gpd.read_file(poi_file)
    roads = gpd.read_file(road_file)
    
    logger.info(f"  网格单元数: {len(grid)}")
    logger.info(f"  POI 数量: {len(poi)}")
    logger.info(f"  路网条数: {len(roads)}")
    
    # 2. 特征提取
    logger.info("\n步骤 2: 提取空间特征")
    extractor = FeatureExtractor()
    
    features = extractor.extract_all_features(
        units=grid,
        poi_data=poi,
        roads_data=roads
    )
    
    logger.info(f"  提取特征维度: {len(features.columns) - 2}")  # 减去 geometry 和 unit_id
    logger.info(f"  特征列表: {[col for col in features.columns if col not in ['geometry', 'unit_id']][:10]}...")
    
    # 显示部分统计
    sample_features = ['poi_density_500m', 'road_density', 'dist_to_road_main']
    for feat in sample_features:
        if feat in features.columns:
            logger.info(f"    {feat}: min={features[feat].min():.2f}, max={features[feat].max():.2f}, mean={features[feat].mean():.2f}")
    
    # 3. 适宜性评价
    logger.info("\n步骤 3: 适宜性评价")
    rules_file = project_root / 'backend' / 'spatial_analysis' / 'function_rules.yaml'
    
    evaluator = SuitabilityEvaluator(rules_config_path=str(rules_file))
    
    evaluation, details = evaluator.evaluate_all_functions(features)
    
    logger.info(f"  评价完成，包含功能类型: {evaluator.function_types}")
    
    # 显示部分得分统计
    for func_type in evaluator.function_types:
        score_col = f'score_{func_type}'
        if score_col in evaluation.columns:
            scores = evaluation[score_col]
            logger.info(f"    {func_type}: min={scores.min():.3f}, max={scores.max():.3f}, mean={scores.mean():.3f}")
    
    # 4. 功能推荐 - 测试三种模式
    logger.info("\n步骤 4: 功能推荐")
    
    # 4.1 最大得分模式
    logger.info("\n  4.1 最大得分模式")
    recommender_max = FunctionRecommender(
        mode='max_score',
        min_acceptable_score=0.4,
        spatial_coordination=False
    )
    
    result_max = recommender_max.recommend(evaluation, evaluator.function_types)
    
    # 4.2 平衡模式
    logger.info("\n  4.2 平衡模式")
    recommender_balanced = FunctionRecommender(
        mode='balanced',
        min_acceptable_score=0.4,
        spatial_coordination=False
    )
    
    result_balanced = recommender_balanced.recommend(evaluation, evaluator.function_types)
    
    # 4.3 空间协调模式
    logger.info("\n  4.3 空间协调模式")
    recommender_coordinated = FunctionRecommender(
        mode='max_score',
        min_acceptable_score=0.4,
        spatial_coordination=True
    )
    
    result_coordinated = recommender_coordinated.recommend(evaluation, evaluator.function_types)
    
    # 5. 对比三种模式的结果
    logger.info("\n步骤 5: 结果对比")
    
    modes = [
        ('最大得分', result_max),
        ('平衡分配', result_balanced),
        ('空间协调', result_coordinated)
    ]
    
    for mode_name, result in modes:
        logger.info(f"\n  {mode_name}模式:")
        func_counts = result['recommended_function'].value_counts()
        total = len(result[result['recommended_function'] != '待定'])
        
        for func, count in func_counts.items():
            ratio = count / len(result) * 100
            logger.info(f"    {func}: {count} ({ratio:.1f}%)")
    
    # 6. 保存结果
    logger.info("\n步骤 6: 保存结果")
    output_dir = data_dir / 'analysis_results'
    output_dir.mkdir(exist_ok=True)
    
    # 保存特征数据
    features_output = output_dir / 'features.geojson'
    features.to_file(features_output, driver='GeoJSON')
    logger.info(f"  特征数据已保存: {features_output}")
    
    # 保存评价结果
    evaluation_output = output_dir / 'evaluation.geojson'
    evaluation.to_file(evaluation_output, driver='GeoJSON')
    logger.info(f"  评价结果已保存: {evaluation_output}")
    
    # 保存推荐结果（空间协调版本）
    recommendation_output = output_dir / 'recommendation.geojson'
    result_coordinated.to_file(recommendation_output, driver='GeoJSON')
    logger.info(f"  推荐结果已保存: {recommendation_output}")
    
    # 7. 详细分析示例单元
    logger.info("\n步骤 7: 示例单元详细分析")
    
    # 选择几个有代表性的单元
    sample_units = result_coordinated.nlargest(3, 'recommendation_score')
    
    for idx, unit in sample_units.iterrows():
        logger.info(f"\n  单元 {unit['unit_id']}:")
        logger.info(f"    推荐功能: {unit['recommended_function']}")
        logger.info(f"    推荐得分: {unit['recommendation_score']:.3f}")
        
        # 显示各功能得分
        logger.info(f"    各功能适宜性:")
        for func_type in evaluator.function_types:
            score_col = f'score_{func_type}'
            if score_col in unit.index:
                logger.info(f"      {func_type}: {unit[score_col]:.3f}")
        
        # 显示关键特征
        logger.info(f"    关键特征:")
        key_features = ['poi_density_500m', 'road_density', 'area']
        for feat in key_features:
            if feat in unit.index:
                logger.info(f"      {feat}: {unit[feat]:.4f}")
    
    logger.info("\n" + "=" * 60)
    logger.info("空间分析模块测试完成")
    logger.info("=" * 60)
    logger.info(f"\n结果文件保存在: {output_dir}")
    logger.info("可以使用 QGIS 或其他 GIS 工具查看 GeoJSON 结果")


if __name__ == '__main__':
    test_full_spatial_analysis()