"""
为测试区域生成简化的路网数据
由于OSM下载可能较慢，这个脚本基于边界快速生成测试用路网
"""

import geopandas as gpd
import numpy as np
from pathlib import Path
from shapely.geometry import LineString
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_grid_roads(boundary_gdf: gpd.GeoDataFrame, output_file: Path):
    """
    生成网格状路网（模拟城市道路）
    
    Args:
        boundary_gdf: 边界数据
        output_file: 输出文件路径
    """
    logger.info("生成测试路网数据...")
    
    # 获取边界范围
    bounds = boundary_gdf.total_bounds  # minx, miny, maxx, maxy
    minx, miny, maxx, maxy = bounds
    
    # 计算间距（约200米的经纬度差）
    spacing_lat = 0.002  # 约200米
    spacing_lon = 0.002
    
    roads = []
    road_id = 1
    
    # 生成南北向道路
    logger.info("  生成南北向道路...")
    x = minx
    while x <= maxx:
        line = LineString([(x, miny), (x, maxy)])
        # 根据位置确定道路等级（中心主干道，两边次干道和支路）
        center_x = (minx + maxx) / 2
        dist_from_center = abs(x - center_x)
        
        if dist_from_center < spacing_lon:
            road_level = 2  # 主干道
            name = f"主干道{road_id}"
        elif dist_from_center < spacing_lon * 3:
            road_level = 3  # 次干道
            name = f"次干道{road_id}"
        else:
            road_level = 4  # 支路
            name = f"支路{road_id}"
        
        roads.append({
            'name': name,
            'road_level': road_level,
            'geometry': line
        })
        
        x += spacing_lon
        road_id += 1
    
    # 生成东西向道路
    logger.info("  生成东西向道路...")
    y = miny
    while y <= maxy:
        line = LineString([(minx, y), (maxx, y)])
        
        # 根据位置确定道路等级
        center_y = (miny + maxy) / 2
        dist_from_center = abs(y - center_y)
        
        if dist_from_center < spacing_lat:
            road_level = 2  # 主干道
            name = f"主干道{road_id}"
        elif dist_from_center < spacing_lat * 3:
            road_level = 3  # 次干道
            name = f"次干道{road_id}"
        else:
            road_level = 4  # 支路
            name = f"支路{road_id}"
        
        roads.append({
            'name': name,
            'road_level': road_level,
            'geometry': line
        })
        
        y += spacing_lat
        road_id += 1
    
    # 创建GeoDataFrame
    roads_gdf = gpd.GeoDataFrame(roads, crs='EPSG:4326')
    
    # 裁剪到边界内
    logger.info("  裁剪路网到边界范围...")
    roads_gdf = gpd.overlay(
        roads_gdf,
        boundary_gdf,
        how='intersection',
        keep_geom_type=True
    )
    
    # 保存
    roads_gdf.to_file(output_file, driver='GeoJSON')
    
    logger.info(f"路网数据已保存: {output_file}")
    logger.info(f"  总计: {len(roads_gdf)} 条道路")
    logger.info(f"  等级统计:")
    for level, count in roads_gdf['road_level'].value_counts().sort_index().items():
        level_name = {1: '快速路', 2: '主干道', 3: '次干道', 4: '支路'}.get(level, '未知')
        logger.info(f"    {level_name}: {count}")
    
    return roads_gdf


def main():
    """主函数"""
    data_dir = Path(__file__).parent.parent / "test_data_osm"
    
    # 读取边界
    boundary_file = data_dir / "boundary.geojson"
    if not boundary_file.exists():
        logger.error(f"边界文件不存在: {boundary_file}")
        return
    
    boundary = gpd.read_file(boundary_file)
    logger.info(f"已读取边界: {boundary_file}")
    
    # 生成路网
    output_file = data_dir / "roads.geojson"
    generate_grid_roads(boundary, output_file)
    
    logger.info("完成！")


if __name__ == "__main__":
    main()