"""
栅格数据处理测试
生成示例DEM数据并测试栅格处理功能
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import geopandas as gpd
from shapely.geometry import box
import rasterio
from rasterio.transform import from_bounds
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


def generate_sample_dem():
    """生成示例DEM数据"""
    logger.info("生成示例DEM...")
    
    # 读取已有边界数据获取实际范围
    boundary_path = OUTPUT_DIR / "boundary_normalized.geojson"
    if boundary_path.exists():
        boundary = gpd.read_file(boundary_path)
        bounds = boundary.total_bounds  # (minx, miny, maxx, maxy)
        logger.info(f"使用实际边界范围: {bounds}")
    else:
        # 默认范围
        bounds = (113.0, 23.0, 113.002, 23.002)
        logger.warning("边界文件不存在，使用默认范围")
    
    # 生成高程数据（模拟起伏地形）
    width, height = 200, 200
    x = np.linspace(0, 4 * np.pi, width)
    y = np.linspace(0, 4 * np.pi, height)
    X, Y = np.meshgrid(x, y)
    
    # 基础高程 + 起伏
    base_elevation = 50  # 基准海拔50米
    elevation = base_elevation + 20 * np.sin(X) * np.cos(Y) + 10 * np.random.randn(height, width) * 0.5
    
    # 确保非负
    elevation = np.maximum(elevation, 0)
    
    # 定义变换
    transform = from_bounds(*bounds, width, height)
    
    # 保存为GeoTIFF
    output_path = SAMPLE_DIR / "sample_dem.tif"
    
    with rasterio.open(
        output_path,
        'w',
        driver='GTiff',
        height=height,
        width=width,
        count=1,
        dtype=elevation.dtype,
        crs='EPSG:4326',
        transform=transform,
        nodata=-9999
    ) as dst:
        dst.write(elevation, 1)
    
    logger.info(f"DEM已保存: {output_path}")
    logger.info(f"  高程范围: {elevation.min():.1f} - {elevation.max():.1f} 米")
    logger.info(f"  地理范围: {bounds}")
    
    return str(output_path)


def generate_sample_landuse():
    """生成示例土地利用栅格"""
    logger.info("生成示例土地利用数据...")
    
    # 读取已有边界数据获取实际范围
    boundary_path = OUTPUT_DIR / "boundary_normalized.geojson"
    if boundary_path.exists():
        boundary = gpd.read_file(boundary_path)
        bounds = boundary.total_bounds
    else:
        bounds = (113.0, 23.0, 113.002, 23.002)
    
    width, height = 200, 200
    
    # 生成土地利用分类（1-6）
    # 模拟空间聚类的土地利用模式
    landuse = np.zeros((height, width), dtype=np.uint8)
    
    # 中心区域为建设用地
    center_mask = np.sqrt((np.arange(height)[:, None] - height/2)**2 + 
                          (np.arange(width) - width/2)**2) < 50
    landuse[center_mask] = 5  # 建设用地
    
    # 周边为耕地和林地
    ring1_mask = np.sqrt((np.arange(height)[:, None] - height/2)**2 + 
                         (np.arange(width) - width/2)**2) < 80
    landuse[ring1_mask & ~center_mask] = 1  # 耕地
    
    # 外围为林地
    landuse[~ring1_mask] = 2  # 林地
    
    # 随机添加一些水域
    water_points = np.random.choice(height * width, size=100, replace=False)
    water_y, water_x = np.unravel_index(water_points, (height, width))
    for y, x in zip(water_y, water_x):
        # 水域周围3x3区域
        y_slice = slice(max(0, y-1), min(height, y+2))
        x_slice = slice(max(0, x-1), min(width, x+2))
        landuse[y_slice, x_slice] = 4  # 水域
    
    # 定义变换
    transform = from_bounds(*bounds, width, height)
    
    # 保存
    output_path = SAMPLE_DIR / "sample_landuse.tif"
    
    with rasterio.open(
        output_path,
        'w',
        driver='GTiff',
        height=height,
        width=width,
        count=1,
        dtype=landuse.dtype,
        crs='EPSG:4326',
        transform=transform,
        nodata=0
    ) as dst:
        dst.write(landuse, 1)
    
    logger.info(f"土地利用栅格已保存: {output_path}")
    
    # 统计
    unique, counts = np.unique(landuse[landuse > 0], return_counts=True)
    logger.info("土地利用分布:")
    landuse_names = {1: "耕地", 2: "林地", 4: "水域", 5: "建设用地"}
    for val, count in zip(unique, counts):
        logger.info(f"  {landuse_names.get(val, '未知')}: {count} 像元 ({count/landuse.size*100:.1f}%)")
    
    return str(output_path)


def test_raster_processing():
    """测试栅格处理功能"""
    from backend.data_processor.raster_processor import (
        RasterProcessor, process_dem_for_analysis, process_landuse_raster
    )
    
    logger.info("\n" + "="*60)
    logger.info("测试栅格数据处理")
    logger.info("="*60)
    
    # 生成测试数据
    dem_path = generate_sample_dem()
    landuse_path = generate_sample_landuse()
    
    # 加载边界和网格
    boundary = gpd.read_file(OUTPUT_DIR / "boundary_normalized.geojson")
    grid = gpd.read_file(OUTPUT_DIR / "grid_square_100m.geojson")
    
    # 只取前50个网格进行测试
    grid_sample = grid.head(50).copy()
    
    logger.info(f"\n使用边界和 {len(grid_sample)} 个网格单元进行测试")
    
    # 测试DEM处理
    logger.info("\n--- 测试DEM处理 ---")
    processor = RasterProcessor()
    
    # 1. 加载栅格
    dem_data, dem_meta = processor.load_raster(dem_path)
    logger.info(f"DEM数据shape: {dem_data.shape}")
    
    # 2. 裁剪到边界
    clipped_dem_path = OUTPUT_DIR / "dem_clipped.tif"
    clipped_data, clipped_meta = processor.clip_by_boundary(
        dem_path, boundary, output_path=str(clipped_dem_path)
    )
    
    # 3. 计算坡度
    slope_path = OUTPUT_DIR / "slope.tif"
    slope_data, slope_meta = processor.calculate_slope(
        str(clipped_dem_path), output_path=str(slope_path), unit='degree'
    )
    logger.info(f"坡度范围: {slope_data.min():.1f} - {slope_data.max():.1f} 度")
    
    # 4. 完整DEM处理流程
    logger.info("\n完整DEM处理流程...")
    result = process_dem_for_analysis(
        dem_path, boundary, grid_sample, output_dir=str(OUTPUT_DIR)
    )
    
    logger.info("\n提取的地形特征:")
    terrain_cols = ['elevation_mean', 'elevation_min', 'elevation_max', 'slope_mean', 'slope_max']
    for col in terrain_cols:
        if col in result.columns:
            logger.info(f"  {col}: {result[col].mean():.2f} (均值)")
    
    # 保存结果
    result_path = OUTPUT_DIR / "grid_with_terrain.geojson"
    result.to_file(result_path, driver='GeoJSON')
    logger.info(f"\n带地形特征的网格已保存: {result_path}")
    
    # 测试土地利用处理
    logger.info("\n--- 测试土地利用处理 ---")
    landuse_result = process_landuse_raster(landuse_path, grid_sample)
    
    logger.info("\n提取的土地利用特征:")
    landuse_cols = [col for col in landuse_result.columns if col.startswith('landuse_') and col.endswith('_ratio')]
    for col in landuse_cols[:5]:  # 只显示前5个
        if landuse_result[col].dtype in ['float64', 'float32', 'int64', 'int32']:
            logger.info(f"  {col}: {landuse_result[col].mean():.3f} (均值)")
        else:
            logger.info(f"  {col}: 类型={landuse_result[col].dtype}")
    
    # 保存结果
    lu_result_path = OUTPUT_DIR / "grid_with_landuse.geojson"
    landuse_result.to_file(lu_result_path, driver='GeoJSON')
    logger.info(f"\n带土地利用特征的网格已保存: {lu_result_path}")
    
    logger.info("\n" + "="*60)
    logger.info("栅格数据处理测试完成")
    logger.info("="*60)


if __name__ == "__main__":
    test_raster_processing()