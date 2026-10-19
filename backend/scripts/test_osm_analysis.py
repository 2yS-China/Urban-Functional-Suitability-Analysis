"""
测试OSM真实数据的完整分析流程
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import geopandas as gpd
import logging
from data_processor.normalizer import DataNormalizer
from data_processor.grid_generator import GridGenerator
from spatial_analysis.feature_extractor import FeatureExtractor
from spatial_analysis.suitability_evaluator import SuitabilityEvaluator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_osm_data_analysis():
    """测试OSM数据的完整分析流程"""
    
    # 数据目录
    data_dir = Path(__file__).parent.parent / "test_data_osm"
    output_dir = Path(__file__).parent.parent / "test_output_osm"
    output_dir.mkdir(exist_ok=True)
    
    logger.info("="*60)
    logger.info("开始测试OSM真实数据分析流程")
    logger.info("="*60)
    
    # 1. 检查数据文件
    logger.info("\n1. 检查数据文件...")
    required_files = {
        'boundary': data_dir / "boundary.geojson",
        'poi': data_dir / "poi.geojson",
        'roads': data_dir / "roads.geojson"
    }
    
    missing_files = []
    for name, path in required_files.items():
        if path.exists():
            logger.info(f"  ✓ {name}: {path}")
        else:
            logger.warning(f"  ✗ {name}: {path} (缺失)")
            missing_files.append(name)
    
    if missing_files:
        logger.error(f"缺少必需文件: {missing_files}")
        logger.info("请先运行 download_osm_data.py 下载数据")
        return
    
    # 2. 加载数据
    logger.info("\n2. 加载数据...")
    boundary = gpd.read_file(required_files['boundary'])
    poi_data = gpd.read_file(required_files['poi'])
    roads_data = gpd.read_file(required_files['roads'])
    
    logger.info(f"  边界: {len(boundary)} 个面")
    logger.info(f"  POI: {len(poi_data)} 个点")
    logger.info(f"  路网: {len(roads_data)} 条路")
    
    # 3. 数据标准化
    logger.info("\n3. 数据标准化...")
    normalizer = DataNormalizer()
    
    boundary_norm = normalizer.normalize_boundary(boundary)
    poi_norm = normalizer.normalize_poi(poi_data)
    roads_norm = normalizer.normalize_roads(roads_data)
    
    logger.info("  数据标准化完成")
    
    # 4. 生成分析网格
    logger.info("\n4. 生成分析网格...")
    grid_gen = GridGenerator()
    
    # 根据区域大小自适应网格尺寸（单位：度）
    area_km2 = boundary_norm.geometry.area.sum() * 111 * 111  # 粗略转换为平方公里
    
    if area_km2 < 5:
        grid_size_degrees = 0.001  # 约111米
    elif area_km2 < 20:
        grid_size_degrees = 0.002  # 约222米
    else:
        grid_size_degrees = 0.003  # 约333米
    
    logger.info(f"  区域面积约: {area_km2:.2f} 平方公里")
    logger.info(f"  选择网格尺寸: {grid_size_degrees} 度 (约 {grid_size_degrees * 111:.0f}米)")
    
    grids = grid_gen.generate_grid(
        boundary_norm,
        grid_size=grid_size_degrees,
        mode='square',
        overlap_threshold=0.3  # 降低阈值以保留更多网格
    )
    
    logger.info(f"  生成网格数: {len(grids)}")
    
    # 保存网格
    grid_file = output_dir / "analysis_grids.geojson"
    grids.to_file(grid_file, driver='GeoJSON')
    logger.info(f"  网格已保存: {grid_file}")
    
    # 5. 特征提取
    logger.info("\n5. 提取空间特征...")
    extractor = FeatureExtractor()
    
    # 基础特征提取
    features = extractor.extract_all_features(
        units=grids,
        poi_data=poi_norm,
        roads_data=roads_norm
    )
    
    logger.info(f"  提取特征数: {len(features.columns) - len(grids.columns)}")
    logger.info(f"  特征列表:")
    feature_cols = [col for col in features.columns if col not in grids.columns]
    for i, col in enumerate(feature_cols[:10], 1):  # 只显示前10个
        logger.info(f"    {i}. {col}")
    if len(feature_cols) > 10:
        logger.info(f"    ... 还有 {len(feature_cols) - 10} 个特征")
    
    # 注意：因为没有栅格数据和约束数据，暂时跳过派生特征计算
    # features = extractor.calculate_derived_features(features)
    # logger.info(f"  派生特征后总特征数: {len(features.columns) - len(grids.columns)}")
    
    # 保存特征数据
    feature_file = output_dir / "features.geojson"
    features.to_file(feature_file, driver='GeoJSON')
    logger.info(f"  特征数据已保存: {feature_file}")
    
    # 6. 适宜性评价
    logger.info("\n6. 进行适宜性评价...")
    evaluator = SuitabilityEvaluator()
    
    results, detailed_scores = evaluator.evaluate_all_functions(features)
    
    logger.info(f"  评价完成，生成评分列:")
    score_cols = [col for col in results.columns if col.startswith('score_')]
    for col in score_cols:
        avg_score = results[col].mean()
        max_score = results[col].max()
        logger.info(f"    {col}: 平均={avg_score:.3f}, 最大={max_score:.3f}")
    
    # 7. 功能推荐
    logger.info("\n7. 生成功能推荐...")
    from spatial_analysis.recommender import FunctionRecommender
    
    # 获取功能类型列表
    function_types = ['居住', '商业', '办公', '工业', '公共服务', '绿地休闲', '综合']
    
    recommender = FunctionRecommender()
    recommendations = recommender.recommend(results, function_types)
    
    logger.info("  推荐统计:")
    for func, count in recommendations['recommended_function'].value_counts().items():
        percentage = count / len(recommendations) * 100
        logger.info(f"    {func}: {count} 个网格 ({percentage:.1f}%)")
    
    # 保存最终结果
    result_file = output_dir / "suitability_results.geojson"
    recommendations.to_file(result_file, driver='GeoJSON')
    logger.info(f"\n最终结果已保存: {result_file}")
    
    # 8. 生成统计报告
    logger.info("\n8. 生成统计报告...")
    generate_report(recommendations, output_dir)
    
    logger.info("\n" + "="*60)
    logger.info("测试完成！")
    logger.info(f"所有结果文件保存在: {output_dir}")
    logger.info("="*60)


def generate_report(results: gpd.GeoDataFrame, output_dir: Path):
    """生成统计报告"""
    
    report = []
    report.append("# OSM数据适宜性分析报告\n")
    
    # 1. 总体统计
    report.append("## 1. 分析单元统计\n")
    report.append(f"- 总网格数: {len(results)}\n")
    report.append(f"- 分析区域面积: {results.geometry.area.sum() * 111000 * 111000 / 1e6:.2f} 平方公里\n")
    report.append(f"- 平均网格面积: {results.geometry.area.mean() * 111000 * 111000:.0f} 平方米\n\n")
    
    # 2. 功能推荐统计
    report.append("## 2. 功能推荐分布\n\n")
    func_stats = results['recommended_function'].value_counts()
    report.append("| 功能类型 | 网格数 | 占比 | 平均评分 |\n")
    report.append("|---------|--------|------|----------|\n")
    
    for func, count in func_stats.items():
        percentage = count / len(results) * 100
        score_col = f'score_{func}'
        if score_col in results.columns:
            avg_score = results[results['recommended_function'] == func][score_col].mean()
            report.append(f"| {func} | {count} | {percentage:.1f}% | {avg_score:.3f} |\n")
    
    report.append("\n")
    
    # 3. 各功能适宜性概况
    report.append("## 3. 各功能适宜性分析\n\n")
    
    score_cols = [col for col in results.columns if col.startswith('score_')]
    for col in score_cols:
        func_name = col.replace('score_', '')
        report.append(f"### {func_name}\n")
        report.append(f"- 平均分: {results[col].mean():.3f}\n")
        report.append(f"- 最高分: {results[col].max():.3f}\n")
        report.append(f"- 最低分: {results[col].min():.3f}\n")
        report.append(f"- 高适宜区（>0.7）: {(results[col] > 0.7).sum()} 个网格\n")
        report.append(f"- 中适宜区（0.5-0.7）: {((results[col] >= 0.5) & (results[col] <= 0.7)).sum()} 个网格\n")
        report.append(f"- 低适宜区（<0.5）: {(results[col] < 0.5).sum()} 个网格\n\n")
    
    # 4. 空间特征概况
    report.append("## 4. 空间特征统计\n\n")
    
    key_features = [
        'road_accessibility', 'population_density_1000m', 'green_density_500m',
        'poi_density_commercial_500m', 'dist_to_metro'
    ]
    
    for feat in key_features:
        if feat in results.columns:
            report.append(f"### {feat}\n")
            report.append(f"- 均值: {results[feat].mean():.2f}\n")
            report.append(f"- 中位数: {results[feat].median():.2f}\n")
            report.append(f"- 标准差: {results[feat].std():.2f}\n\n")
    
    # 保存报告
    report_file = output_dir / "analysis_report.md"
    report_file.write_text(''.join(report), encoding='utf-8')
    logger.info(f"  报告已保存: {report_file}")


if __name__ == "__main__":
    test_osm_data_analysis()