"""
快速创建完整的测试数据集
生成边界、POI和路网数据用于测试
"""

import geopandas as gpd
import numpy as np
from pathlib import Path
from shapely.geometry import Point, LineString, Polygon
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_complete_test_data():
    """创建完整测试数据"""
    
    data_dir = Path(__file__).parent.parent / "test_data_osm"
    data_dir.mkdir(exist_ok=True)
    
    logger.info("创建测试数据集...")
    
    # 1. 创建边界（约4km x 4km的区域）
    logger.info("  1. 创建边界...")
    center_lon, center_lat = 116.325, 40.000
    size = 0.02  # 约2.2公里
    
    boundary_coords = [
        (center_lon - size, center_lat - size),
        (center_lon + size, center_lat - size),
        (center_lon + size, center_lat + size),
        (center_lon - size, center_lat + size),
        (center_lon - size, center_lat - size)
    ]
    
    boundary = gpd.GeoDataFrame(
        {'name': ['测试区域']},
        geometry=[Polygon(boundary_coords)],
        crs='EPSG:4326'
    )
    
    boundary_file = data_dir / "boundary.geojson"
    boundary.to_file(boundary_file, driver='GeoJSON')
    logger.info(f"     边界已保存: {len(boundary)} 个面")
    
    # 2. 创建POI（模拟各类设施）
    logger.info("  2. 创建POI...")
    np.random.seed(42)
    
    poi_categories = {
        '交通设施': 30,
        '商业服务': 80,
        '公共服务': 40,
        '绿地公园': 20,
        '办公场所': 50
    }
    
    pois = []
    for category, count in poi_categories.items():
        for i in range(count):
            lon = np.random.uniform(center_lon - size*0.9, center_lon + size*0.9)
            lat = np.random.uniform(center_lat - size*0.9, center_lat + size*0.9)
            pois.append({
                'category': category,
                'name': f'{category}_{i+1}',
                'geometry': Point(lon, lat)
            })
    
    poi_gdf = gpd.GeoDataFrame(pois, crs='EPSG:4326')
    poi_file = data_dir / "poi.geojson"
    poi_gdf.to_file(poi_file, driver='GeoJSON')
    logger.info(f"     POI已保存: {len(poi_gdf)} 个点")
    
    # 3. 创建路网（网格状）
    logger.info("  3. 创建路网...")
    roads = []
    road_id = 1
    
    # 主干道间距约800米
    main_spacing = 0.008
    # 次干道间距约400米
    secondary_spacing = 0.004
    
    # 南北向道路
    for i, x in enumerate(np.arange(center_lon - size, center_lon + size, secondary_spacing)):
        line = LineString([(x, center_lat - size), (x, center_lat + size)])
        
        # 根据位置分配等级
        if i % 2 == 0:
            road_level = 2  # 主干道
            name = f"南北主干道{road_id}"
        else:
            road_level = 3  # 次干道
            name = f"南北次干道{road_id}"
        
        roads.append({
            'name': name,
            'road_level': road_level,
            'geometry': line
        })
        road_id += 1
    
    # 东西向道路
    for i, y in enumerate(np.arange(center_lat - size, center_lat + size, secondary_spacing)):
        line = LineString([(center_lon - size, y), (center_lon + size, y)])
        
        if i % 2 == 0:
            road_level = 2
            name = f"东西主干道{road_id}"
        else:
            road_level = 3
            name = f"东西次干道{road_id}"
        
        roads.append({
            'name': name,
            'road_level': road_level,
            'geometry': line
        })
        road_id += 1
    
    roads_gdf = gpd.GeoDataFrame(roads, crs='EPSG:4326')
    roads_file = data_dir / "roads.geojson"
    roads_gdf.to_file(roads_file, driver='GeoJSON')
    logger.info(f"     路网已保存: {len(roads_gdf)} 条道路")
    
    # 4. 创建README
    readme = f"""# 测试数据集

## 数据说明
- 区域中心: ({center_lon}, {center_lat})
- 区域范围: 约 {size*2*111:.1f}km x {size*2*111:.1f}km
- 创建时间: 自动生成

## 数据文件
1. **boundary.geojson** - 边界数据 ({len(boundary)} 个面)
2. **poi.geojson** - POI数据 ({len(poi_gdf)} 个点)
3. **roads.geojson** - 路网数据 ({len(roads_gdf)} 条道路)

## POI分类
- 交通设施: {poi_categories['交通设施']} 个
- 商业服务: {poi_categories['商业服务']} 个
- 公共服务: {poi_categories['公共服务']} 个
- 绿地公园: {poi_categories['绿地公园']} 个
- 办公场所: {poi_categories['办公场所']} 个

## 路网等级
- 主干道: {(roads_gdf['road_level'] == 2).sum()} 条
- 次干道: {(roads_gdf['road_level'] == 3).sum()} 条

## 使用说明
此数据集用于测试城市片区功能适宜性分析系统。数据为模拟生成，可直接用于测试完整分析流程。
"""
    
    readme_file = data_dir / "README.md"
    readme_file.write_text(readme, encoding='utf-8')
    logger.info(f"     README已保存: {readme_file}")
    
    logger.info("\n测试数据集创建完成！")
    logger.info(f"数据目录: {data_dir}")
    logger.info(f"- boundary.geojson ({len(boundary)} 个面)")
    logger.info(f"- poi.geojson ({len(poi_gdf)} 个点)")
    logger.info(f"- roads.geojson ({len(roads_gdf)} 条道路)")


if __name__ == "__main__":
    create_complete_test_data()