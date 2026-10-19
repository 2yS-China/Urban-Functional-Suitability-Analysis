"""
从OpenStreetMap下载真实数据用于测试
使用OSMnx库获取指定区域的POI、路网、建筑物等数据
"""

import osmnx as ox
import geopandas as gpd
import pandas as pd
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def download_area_boundary(place_name: str, output_dir: Path):
    """
    下载区域边界
    
    Args:
        place_name: 地名（如 "海淀区, 北京市, 中国"）
        output_dir: 输出目录
    """
    logger.info(f"下载区域边界: {place_name}")
    
    try:
        # 获取行政边界
        gdf = ox.geocode_to_gdf(place_name)
        
        # 保存为GeoJSON
        output_file = output_dir / "boundary.geojson"
        gdf.to_file(output_file, driver='GeoJSON')
        
        logger.info(f"边界数据已保存: {output_file}")
        logger.info(f"  面积: {gdf.geometry.area.values[0] * 111000 * 111000 / 1e6:.2f} 平方公里")
        
        return gdf
    
    except Exception as e:
        logger.error(f"下载边界失败: {e}")
        return None


def download_pois(boundary_gdf: gpd.GeoDataFrame, output_dir: Path):
    """
    下载POI数据
    
    Args:
        boundary_gdf: 边界GeoDataFrame
        output_dir: 输出目录
    """
    logger.info("下载POI数据...")
    
    # 定义POI类别映射
    poi_categories = {
        '交通设施': {
            'tags': {'public_transport': True, 'railway': 'station', 'aeroway': 'aerodrome'},
            'category': '交通设施'
        },
        '商业服务': {
            'tags': {'shop': True, 'amenity': ['restaurant', 'cafe', 'fast_food', 'bar']},
            'category': '商业服务'
        },
        '公共服务': {
            'tags': {'amenity': ['school', 'hospital', 'clinic', 'library', 'community_centre']},
            'category': '公共服务'
        },
        '绿地公园': {
            'tags': {'leisure': ['park', 'garden'], 'natural': 'wood'},
            'category': '绿地公园'
        },
        '办公场所': {
            'tags': {'office': True, 'building': 'office'},
            'category': '办公场所'
        }
    }
    
    all_pois = []
    
    for cat_name, cat_info in poi_categories.items():
        try:
            logger.info(f"  获取 {cat_name}...")
            
            # 获取POI
            pois = ox.features_from_polygon(
                boundary_gdf.geometry.values[0],
                tags=cat_info['tags']
            )
            
            if len(pois) > 0:
                # 转换为点几何（取质心）
                pois_points = pois.copy()
                pois_points.geometry = pois_points.geometry.centroid
                
                # 添加类别标签
                pois_points['category'] = cat_info['category']
                pois_points['name'] = pois_points.get('name', '未命名')
                
                # 只保留必要字段
                pois_simple = pois_points[['category', 'name', 'geometry']].copy()
                
                all_pois.append(pois_simple)
                logger.info(f"    找到 {len(pois_simple)} 个")
        
        except Exception as e:
            logger.warning(f"  获取 {cat_name} 失败: {e}")
    
    if all_pois:
        # 合并所有POI
        poi_gdf = pd.concat(all_pois, ignore_index=True)
        
        # 保存
        output_file = output_dir / "poi.geojson"
        poi_gdf.to_file(output_file, driver='GeoJSON')
        
        logger.info(f"POI数据已保存: {output_file}")
        logger.info(f"  总计: {len(poi_gdf)} 个POI")
        logger.info(f"  分类统计:")
        for cat, count in poi_gdf['category'].value_counts().items():
            logger.info(f"    {cat}: {count}")
        
        return poi_gdf
    
    else:
        logger.warning("未获取到任何POI数据")
        return None


def download_roads(boundary_gdf: gpd.GeoDataFrame, output_dir: Path):
    """
    下载路网数据
    
    Args:
        boundary_gdf: 边界GeoDataFrame
        output_dir: 输出目录
    """
    logger.info("下载路网数据...")
    
    try:
        # 获取路网图
        G = ox.graph_from_polygon(
            boundary_gdf.geometry.values[0],
            network_type='drive'
        )
        
        # 转换为GeoDataFrame
        edges = ox.graph_to_gdfs(G, nodes=False)
        
        # 道路等级映射
        def classify_road(row):
            highway = row.get('highway', '')
            if isinstance(highway, list):
                highway = highway[0]
            
            if highway in ['motorway', 'motorway_link', 'trunk', 'trunk_link']:
                return 1  # 快速路
            elif highway in ['primary', 'primary_link']:
                return 2  # 主干道
            elif highway in ['secondary', 'secondary_link', 'tertiary', 'tertiary_link']:
                return 3  # 次干道
            else:
                return 4  # 支路
        
        edges['road_level'] = edges.apply(classify_road, axis=1)
        edges['name'] = edges.get('name', '未命名道路')
        
        # 简化字段
        roads_simple = edges[['name', 'road_level', 'geometry']].copy()
        
        # 保存
        output_file = output_dir / "roads.geojson"
        roads_simple.to_file(output_file, driver='GeoJSON')
        
        logger.info(f"路网数据已保存: {output_file}")
        logger.info(f"  总计: {len(roads_simple)} 条道路")
        logger.info(f"  等级统计:")
        for level, count in roads_simple['road_level'].value_counts().sort_index().items():
            level_name = {1: '快速路', 2: '主干道', 3: '次干道', 4: '支路'}.get(level, '未知')
            logger.info(f"    {level_name}: {count}")
        
        return roads_simple
    
    except Exception as e:
        logger.error(f"下载路网失败: {e}")
        return None


def download_water_bodies(boundary_gdf: gpd.GeoDataFrame, output_dir: Path):
    """
    下载水体数据
    
    Args:
        boundary_gdf: 边界GeoDataFrame
        output_dir: 输出目录
    """
    logger.info("下载水体数据...")
    
    try:
        # 获取水体
        water = ox.features_from_polygon(
            boundary_gdf.geometry.values[0],
            tags={'natural': ['water'], 'waterway': ['river', 'stream', 'canal']}
        )
        
        if len(water) > 0:
            # 只保留面状水体
            water_polygons = water[water.geometry.type.isin(['Polygon', 'MultiPolygon'])].copy()
            
            if len(water_polygons) > 0:
                water_polygons['water_type'] = water_polygons.get('natural', '河流')
                water_polygons['name'] = water_polygons.get('name', '未命名水体')
                
                # 简化字段
                water_simple = water_polygons[['name', 'water_type', 'geometry']].copy()
                
                # 保存
                output_file = output_dir / "water_bodies.geojson"
                water_simple.to_file(output_file, driver='GeoJSON')
                
                logger.info(f"水体数据已保存: {output_file}")
                logger.info(f"  总计: {len(water_simple)} 个水体")
                
                return water_simple
        
        logger.warning("未找到水体数据")
        return None
    
    except Exception as e:
        logger.warning(f"下载水体失败: {e}")
        return None


def download_green_spaces(boundary_gdf: gpd.GeoDataFrame, output_dir: Path):
    """
    下载绿地数据（可作为现有绿地参考）
    
    Args:
        boundary_gdf: 边界GeoDataFrame
        output_dir: 输出目录
    """
    logger.info("下载绿地数据...")
    
    try:
        green = ox.features_from_polygon(
            boundary_gdf.geometry.values[0],
            tags={'leisure': ['park', 'garden', 'nature_reserve'], 'landuse': ['forest', 'grass']}
        )
        
        if len(green) > 0:
            green_polygons = green[green.geometry.type.isin(['Polygon', 'MultiPolygon'])].copy()
            
            if len(green_polygons) > 0:
                green_polygons['green_type'] = green_polygons.get('leisure', green_polygons.get('landuse', '绿地'))
                green_polygons['name'] = green_polygons.get('name', '未命名绿地')
                
                green_simple = green_polygons[['name', 'green_type', 'geometry']].copy()
                
                output_file = output_dir / "green_spaces.geojson"
                green_simple.to_file(output_file, driver='GeoJSON')
                
                logger.info(f"绿地数据已保存: {output_file}")
                logger.info(f"  总计: {len(green_simple)} 个绿地")
                
                return green_simple
        
        logger.warning("未找到绿地数据")
        return None
    
    except Exception as e:
        logger.warning(f"下载绿地失败: {e}")
        return None


def download_by_bbox(north: float, south: float, east: float, west: float, output_dir: Path):
    """
    使用坐标范围下载数据（更可靠）
    
    Args:
        north, south, east, west: 坐标范围
        output_dir: 输出目录
    """
    from shapely.geometry import box
    
    logger.info(f"使用坐标范围: N={north}, S={south}, E={east}, W={west}")
    
    # 1. 创建边界
    bbox = box(west, south, east, north)
    boundary = gpd.GeoDataFrame({'geometry': [bbox]}, crs='EPSG:4326')
    
    # 保存边界
    boundary_file = output_dir / "boundary.geojson"
    boundary.to_file(boundary_file, driver='GeoJSON')
    logger.info(f"边界已创建: {boundary_file}")
    
    return boundary


def main():
    """主函数"""
    # 设置下载参数
    # 方式1：使用地名（可能因网络问题失败）
    # place_name = "中关村, 海淀区, 北京市, 中国"
    
    # 方式2：使用坐标范围（更可靠）- 北京中关村区域（扩大范围）
    use_bbox = True
    north, south, east, west = 40.020, 39.980, 116.350, 116.300
    
    # 创建输出目录
    output_dir = Path(__file__).parent.parent / "test_data_osm"
    output_dir.mkdir(exist_ok=True)
    
    logger.info("="*60)
    logger.info("开始从OpenStreetMap下载真实数据")
    logger.info(f"输出目录: {output_dir}")
    logger.info("="*60)
    
    # 1. 下载边界
    if use_bbox:
        boundary = download_by_bbox(north, south, east, west, output_dir)
    else:
        place_name = "中关村, 海淀区, 北京市, 中国"
        logger.info(f"目标区域: {place_name}")
        boundary = download_area_boundary(place_name, output_dir)
        if boundary is None:
            logger.error("无法获取边界数据，尝试使用坐标范围")
            boundary = download_by_bbox(north, south, east, west, output_dir)
    
    # 2. 下载POI
    pois = download_pois(boundary, output_dir)
    
    # 3. 下载路网
    roads = download_roads(boundary, output_dir)
    
    # 4. 下载水体
    water = download_water_bodies(boundary, output_dir)
    
    # 5. 下载绿地
    green = download_green_spaces(boundary, output_dir)
    
    logger.info("="*60)
    logger.info("数据下载完成！")
    logger.info(f"数据保存在: {output_dir}")
    logger.info("="*60)
    
    # 生成数据说明文件
    area_desc = f"坐标范围: N={north}, S={south}, E={east}, W={west}" if use_bbox else f"区域: {place_name}"
    readme_content = f"""# OpenStreetMap真实数据

## 数据来源
- {area_desc}
- 数据源: OpenStreetMap
- 下载时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

## 数据文件
1. **boundary.geojson** - 区域边界
2. **poi.geojson** - 兴趣点数据（{len(pois) if pois is not None else 0}个）
3. **roads.geojson** - 路网数据（{len(roads) if roads is not None else 0}条）
4. **water_bodies.geojson** - 水体数据（{len(water) if water is not None else 0}个）
5. **green_spaces.geojson** - 绿地数据（{len(green) if green is not None else 0}个）

## 数据质量说明
- 这些数据来自开放地图社区，质量取决于当地贡献者的维护情况
- 建议作为测试和演示使用
- 实际项目建议使用政府官方数据或商业数据

## 使用说明
1. 将这些数据上传到系统进行测试
2. boundary.geojson和poi.geojson是必需的
3. 其他数据是可选的，可用于测试对应功能

## 下一步
如需下载更多数据类型（DEM、土壤、灾害风险等），需要使用其他数据源：
- DEM: SRTM、ASTER GDEM
- 土壤: FAO Soil Database
- 降水: WorldClim
- GDP: 统计年鉴数据
"""
    
    readme_file = output_dir / "README.md"
    readme_file.write_text(readme_content, encoding='utf-8')
    logger.info(f"数据说明已保存: {readme_file}")


if __name__ == "__main__":
    main()