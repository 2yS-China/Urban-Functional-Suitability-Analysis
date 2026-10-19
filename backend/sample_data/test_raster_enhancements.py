"""
测试栅格增强功能：坡向计算和栅格代数运算
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import geopandas as gpd
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 设置路径
SAMPLE_DIR = Path(__file__).parent
OUTPUT_DIR = SAMPLE_DIR / "processed"
OUTPUT_DIR.mkdir(exist_ok=True)


def test_aspect_calculation():
    """测试坡向计算"""
    from backend.data_processor.raster_processor import RasterProcessor
    
    logger.info("\n" + "="*60)
    logger.info("测试坡向计算")
    logger.info("="*60)
    
    processor = RasterProcessor()
    
    # 检查DEM文件
    dem_path = SAMPLE_DIR / "sample_dem.tif"
    if not dem_path.exists():
        logger.error(f"DEM文件不存在: {dem_path}")
        logger.info("请先运行 test_raster_processing.py 生成示例数据")
        return
    
    # 计算坡向
    logger.info(f"\n从 {dem_path.name} 计算坡向...")
    aspect_path = OUTPUT_DIR / "aspect.tif"
    aspect_data, aspect_meta = processor.calculate_aspect(
        str(dem_path),
        output_path=str(aspect_path),
        unit='degree'
    )
    
    # 统计坡向分布
    logger.info("\n坡向统计:")
    flat_mask = aspect_data == -1
    logger.info(f"  平坦区域: {flat_mask.sum()} 像元 ({flat_mask.sum()/aspect_data.size*100:.1f}%)")
    
    valid_aspect = aspect_data[~flat_mask]
    if len(valid_aspect) > 0:
        logger.info(f"  坡向范围: {valid_aspect.min():.1f}° - {valid_aspect.max():.1f}°")
        logger.info(f"  平均坡向: {valid_aspect.mean():.1f}°")
        
        # 按方向分布统计
        direction_ranges = {
            '北(337.5-22.5°)': ((aspect_data >= 337.5) | (aspect_data < 22.5)) & ~flat_mask,
            '东北(22.5-67.5°)': (aspect_data >= 22.5) & (aspect_data < 67.5),
            '东(67.5-112.5°)': (aspect_data >= 67.5) & (aspect_data < 112.5),
            '东南(112.5-157.5°)': (aspect_data >= 112.5) & (aspect_data < 157.5),
            '南(157.5-202.5°)': (aspect_data >= 157.5) & (aspect_data < 202.5),
            '西南(202.5-247.5°)': (aspect_data >= 202.5) & (aspect_data < 247.5),
            '西(247.5-292.5°)': (aspect_data >= 247.5) & (aspect_data < 292.5),
            '西北(292.5-337.5°)': (aspect_data >= 292.5) & (aspect_data < 337.5)
        }
        
        logger.info("\n方向分布:")
        for direction, mask in direction_ranges.items():
            count = mask.sum()
            percentage = count / aspect_data.size * 100
            logger.info(f"  {direction}: {count} 像元 ({percentage:.1f}%)")
    
    # 测试坡向分类
    logger.info("\n测试坡向分类...")
    
    # 8方向分类
    aspect_8dir = processor.classify_aspect(aspect_data, mode='8_directions')
    unique, counts = np.unique(aspect_8dir, return_counts=True)
    logger.info("\n8方向分类:")
    direction_names = {
        0: '平坦', 1: '北', 2: '东北', 3: '东', 4: '东南',
        5: '南', 6: '西南', 7: '西', 8: '西北'
    }
    for val, count in zip(unique, counts):
        logger.info(f"  {direction_names.get(val, '未知')}: {count} 像元 ({count/aspect_data.size*100:.1f}%)")
    
    # 阴阳坡分类
    aspect_sunny = processor.classify_aspect(aspect_data, mode='sunny_shady')
    unique, counts = np.unique(aspect_sunny, return_counts=True)
    logger.info("\n阴阳坡分类:")
    sunny_names = {0: '平坦', 1: '向阳坡', 2: '背阴坡', 3: '半阴半阳'}
    for val, count in zip(unique, counts):
        logger.info(f"  {sunny_names.get(val, '未知')}: {count} 像元 ({count/aspect_data.size*100:.1f}%)")
    
    logger.info(f"\n坡向栅格已保存: {aspect_path}")


def test_raster_calculator():
    """测试栅格代数运算"""
    from backend.data_processor.raster_processor import RasterProcessor
    
    logger.info("\n" + "="*60)
    logger.info("测试栅格代数运算")
    logger.info("="*60)
    
    processor = RasterProcessor()
    
    # 检查输入文件
    dem_path = SAMPLE_DIR / "sample_dem.tif"
    slope_path = OUTPUT_DIR / "slope.tif"
    
    if not dem_path.exists() or not slope_path.exists():
        logger.error("缺少输入文件")
        logger.info("请先运行 test_raster_processing.py 生成示例数据")
        return
    
    # 测试1: 简单算术运算
    logger.info("\n测试1: 地形起伏度 = 高程 / 100 + 坡度")
    terrain_roughness_path = OUTPUT_DIR / "terrain_roughness.tif"
    result, metadata = processor.raster_calculator(
        expression="dem / 100 + slope",
        rasters={
            "dem": str(dem_path),
            "slope": str(slope_path)
        },
        output_path=str(terrain_roughness_path),
        nodata=-9999
    )
    
    logger.info(f"  结果范围: {result.min():.2f} - {result.max():.2f}")
    logger.info(f"  平均值: {result.mean():.2f}")
    logger.info(f"  已保存: {terrain_roughness_path.name}")
    
    # 测试2: 条件运算
    logger.info("\n测试2: 平坦区域标识（坡度<5度则为1，否则为0）")
    flat_areas_path = OUTPUT_DIR / "flat_areas.tif"
    result2, _ = processor.raster_calculator(
        expression="where(slope < 5, 1, 0)",
        rasters={"slope": str(slope_path)},
        output_path=str(flat_areas_path),
        nodata=-1
    )
    
    flat_count = (result2 == 1).sum()
    total_count = result2.size
    logger.info(f"  平坦区域: {flat_count} 像元 ({flat_count/total_count*100:.1f}%)")
    logger.info(f"  已保存: {flat_areas_path.name}")
    
    # 测试3: 复杂数学运算
    logger.info("\n测试3: 标准化坡度（使用标准差标准化）")
    normalized_slope_path = OUTPUT_DIR / "normalized_slope.tif"
    
    # 先读取坡度数据计算均值和标准差
    import rasterio
    with rasterio.open(slope_path) as src:
        slope_data = src.read(1)
        slope_mean = slope_data.mean()
        slope_std = slope_data.std()
    
    logger.info(f"  坡度均值: {slope_mean:.2f}°")
    logger.info(f"  坡度标准差: {slope_std:.2f}°")
    
    result3, _ = processor.raster_calculator(
        expression=f"(slope - {slope_mean}) / {slope_std}",
        rasters={"slope": str(slope_path)},
        output_path=str(normalized_slope_path),
        nodata=-9999
    )
    
    logger.info(f"  标准化后范围: {result3.min():.2f} - {result3.max():.2f}")
    logger.info(f"  标准化后均值: {result3.mean():.4f} (应接近0)")
    logger.info(f"  标准化后标准差: {result3.std():.4f} (应接近1)")
    logger.info(f"  已保存: {normalized_slope_path.name}")
    
    # 测试4: 多栅格组合指数
    logger.info("\n测试4: 地形综合指数 = 0.6*标准化高程 + 0.4*标准化坡度")
    
    # 标准化高程
    import rasterio
    with rasterio.open(dem_path) as src:
        dem_data = src.read(1)
        dem_mean = dem_data.mean()
        dem_std = dem_data.std()
    
    normalized_dem_path = OUTPUT_DIR / "normalized_dem.tif"
    processor.raster_calculator(
        expression=f"(dem - {dem_mean}) / {dem_std}",
        rasters={"dem": str(dem_path)},
        output_path=str(normalized_dem_path)
    )
    
    # 组合指数
    terrain_index_path = OUTPUT_DIR / "terrain_composite_index.tif"
    result4, _ = processor.raster_calculator(
        expression="0.6 * norm_dem + 0.4 * norm_slope",
        rasters={
            "norm_dem": str(normalized_dem_path),
            "norm_slope": str(normalized_slope_path)
        },
        output_path=str(terrain_index_path),
        nodata=-9999
    )
    
    logger.info(f"  综合指数范围: {result4.min():.2f} - {result4.max():.2f}")
    logger.info(f"  综合指数均值: {result4.mean():.4f}")
    logger.info(f"  已保存: {terrain_index_path.name}")


def test_dem_with_aspect():
    """测试带坡向的DEM完整处理流程"""
    from backend.data_processor.raster_processor import process_dem_for_analysis
    
    logger.info("\n" + "="*60)
    logger.info("测试DEM完整处理（含坡向）")
    logger.info("="*60)
    
    # 加载数据
    dem_path = SAMPLE_DIR / "sample_dem.tif"
    boundary = gpd.read_file(OUTPUT_DIR / "boundary_normalized.geojson")
    grid = gpd.read_file(OUTPUT_DIR / "grid_square_100m.geojson")
    
    # 只取前30个网格进行测试
    grid_sample = grid.head(30).copy()
    
    logger.info(f"\n使用 {len(grid_sample)} 个网格单元测试")
    
    # 处理DEM（包含坡向）
    result = process_dem_for_analysis(
        str(dem_path),
        boundary,
        grid_sample,
        output_dir=str(OUTPUT_DIR),
        include_aspect=True
    )
    
    # 显示结果
    logger.info("\n提取的地形特征:")
    terrain_features = [
        'elevation_mean', 'elevation_min', 'elevation_max',
        'slope_mean', 'slope_max',
        'aspect_mean', 'aspect_dominant'
    ]
    
    for col in terrain_features:
        if col in result.columns:
            if result[col].dtype in ['float64', 'float32', 'int64', 'int32']:
                logger.info(f"  {col}: {result[col].mean():.2f} (均值)")
            else:
                # 对于分类字段，显示分布
                value_counts = result[col].value_counts()
                logger.info(f"  {col} 分布:")
                for val, count in value_counts.head(5).items():
                    logger.info(f"    {val}: {count}个单元")
    
    # 保存结果
    result_path = OUTPUT_DIR / "grid_with_terrain_aspect.geojson"
    result.to_file(result_path, driver='GeoJSON')
    logger.info(f"\n带坡向特征的网格已保存: {result_path}")


if __name__ == "__main__":
    # 测试坡向计算
    test_aspect_calculation()
    
    # 测试栅格代数运算
    test_raster_calculator()
    
    # 测试完整DEM处理（含坡向）
    test_dem_with_aspect()
    
    logger.info("\n" + "="*60)
    logger.info("栅格增强功能测试完成")
    logger.info("="*60)