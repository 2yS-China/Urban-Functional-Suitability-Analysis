"""
生成示例路网数据
模拟城市路网结构
"""

import geopandas as gpd
from shapely.geometry import LineString
import numpy as np
from pathlib import Path
from typing import Tuple


def generate_grid_road_network(
    bounds: Tuple[float, float, float, float],
    spacing: float = 0.005,  # 道路间距（经纬度）
    crs: str = 'EPSG:4326'
) -> gpd.GeoDataFrame:
    """
    生成网格状路网（模拟规整的城市道路）
    
    Args:
        bounds: 边界范围 (minx, miny, maxx, maxy)
        spacing: 道路间距
        crs: 坐标系
        
    Returns:
        路网GeoDataFrame
    """
    minx, miny, maxx, maxy = bounds
    
    roads = []
    
    # 生成南北向道路（纵向）
    x_coords = np.arange(minx, maxx, spacing)
    for i, x in enumerate(x_coords):
        # 交替主干道和支路
        if i % 3 == 0:
            road_type = '主干道'
            width = 40
        elif i % 3 == 1:
            road_type = '次干道'
            width = 30
        else:
            road_type = '支路'
            width = 15
        
        line = LineString([(x, miny), (x, maxy)])
        roads.append({
            'geometry': line,
            'road_type': road_type,
            'name': f'南北{i+1}路',
            'width': width
        })
    
    # 生成东西向道路（横向）
    y_coords = np.arange(miny, maxy, spacing)
    for i, y in enumerate(y_coords):
        if i % 3 == 0:
            road_type = '主干道'
            width = 40
        elif i % 3 == 1:
            road_type = '次干道'
            width = 30
        else:
            road_type = '支路'
            width = 15
        
        line = LineString([(minx, y), (maxx, y)])
        roads.append({
            'geometry': line,
            'road_type': road_type,
            'name': f'东西{i+1}路',
            'width': width
        })
    
    # 添加对角线主干道（模拟穿越性道路）
    diagonal1 = LineString([(minx, miny), (maxx, maxy)])
    roads.append({
        'geometry': diagonal1,
        'road_type': '快速路',
        'name': '西南-东北快速路',
        'width': 50
    })
    
    # 创建GeoDataFrame
    road_gdf = gpd.GeoDataFrame(roads, crs=crs)
    
    return road_gdf


def generate_organic_road_network(
    bounds: Tuple[float, float, float, float],
    num_roads: int = 30,
    crs: str = 'EPSG:4326'
) -> gpd.GeoDataFrame:
    """
    生成有机路网（模拟自然生长的道路）
    
    Args:
        bounds: 边界范围
        num_roads: 道路数量
        crs: 坐标系
        
    Returns:
        路网GeoDataFrame
    """
    minx, miny, maxx, maxy = bounds
    
    roads = []
    
    # 生成主要道路（连接边界到中心）
    center_x = (minx + maxx) / 2
    center_y = (miny + maxy) / 2
    
    # 辐射状主干道
    for i in range(8):
        angle = i * np.pi / 4
        end_x = center_x + (maxx - minx) * 0.5 * np.cos(angle)
        end_y = center_y + (maxy - miny) * 0.5 * np.sin(angle)
        
        line = LineString([(center_x, center_y), (end_x, end_y)])
        roads.append({
            'geometry': line,
            'road_type': '主干道',
            'name': f'放射路{i+1}',
            'width': 40
        })
    
    # 环形路
    for radius_ratio in [0.3, 0.7]:
        radius_x = (maxx - minx) * radius_ratio / 2
        radius_y = (maxy - miny) * radius_ratio / 2
        
        angles = np.linspace(0, 2*np.pi, 20)
        x_coords = center_x + radius_x * np.cos(angles)
        y_coords = center_y + radius_y * np.sin(angles)
        
        line = LineString(zip(x_coords, y_coords))
        roads.append({
            'geometry': line,
            'road_type': '次干道',
            'name': f'环路{int(radius_ratio*10)}',
            'width': 30
        })
    
    # 随机连接道路（支路）
    for i in range(num_roads):
        # 生成随机曲线
        num_points = np.random.randint(3, 6)
        x_coords = np.random.uniform(minx, maxx, num_points)
        y_coords = np.random.uniform(miny, maxy, num_points)
        
        line = LineString(zip(x_coords, y_coords))
        roads.append({
            'geometry': line,
            'road_type': '支路',
            'name': f'支路{i+1}',
            'width': 15
        })
    
    # 创建GeoDataFrame
    road_gdf = gpd.GeoDataFrame(roads, crs=crs)
    
    return road_gdf


def generate_roads_for_boundary(
    boundary_file: str,
    network_type: str = 'grid',
    output_dir: str = "backend/sample_data"
) -> gpd.GeoDataFrame:
    """
    为给定边界生成路网数据
    
    Args:
        boundary_file: 边界文件路径
        network_type: 路网类型（'grid': 网格, 'organic': 有机）
        output_dir: 输出目录
        
    Returns:
        路网GeoDataFrame
    """
    # 读取边界
    boundary = gpd.read_file(boundary_file)
    bounds = boundary.total_bounds
    crs = boundary.crs
    
    print(f"边界范围: {bounds}")
    print(f"生成路网类型: {network_type}")
    
    # 生成路网
    if network_type == 'grid':
        road_gdf = generate_grid_road_network(bounds, spacing=0.003, crs=crs)
    elif network_type == 'organic':
        road_gdf = generate_organic_road_network(bounds, num_roads=30, crs=crs)
    else:
        raise ValueError(f"不支持的路网类型: {network_type}")
    
    # 裁剪到边界内（保留与边界相交的道路）
    boundary_geom = boundary.unary_union
    road_gdf['geometry'] = road_gdf.geometry.intersection(boundary_geom)
    
    # 移除空几何
    road_gdf = road_gdf[~road_gdf.geometry.is_empty]
    
    # 保存
    output_path = Path(output_dir)
    output_file = output_path / f"sample_roads_{network_type}.geojson"
    road_gdf.to_file(output_file, driver='GeoJSON')
    
    print(f"\n[OK] 生成路网数据: {output_file}")
    print(f"  - 道路总数: {len(road_gdf)}")
    print(f"  - 道路类型分布:")
    for road_type in road_gdf['road_type'].value_counts().items():
        print(f"    - {road_type[0]}: {road_type[1]}")
    
    return road_gdf, output_file


if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    print("=" * 60)
    print("生成示例路网数据")
    print("=" * 60)
    print()
    
    # 检查边界文件
    boundary_file = "backend/sample_data/sample_boundary.geojson"
    
    if not Path(boundary_file).exists():
        print(f"错误: 边界文件不存在: {boundary_file}")
        print("请先运行 generate_sample_area.py 生成边界数据")
        sys.exit(1)
    
    # 生成网格路网
    print("1. 生成网格路网...")
    road_gdf1, file1 = generate_roads_for_boundary(
        boundary_file,
        network_type='grid',
        output_dir="backend/sample_data"
    )
    print()
    
    # 生成有机路网
    print("2. 生成有机路网...")
    road_gdf2, file2 = generate_roads_for_boundary(
        boundary_file,
        network_type='organic',
        output_dir="backend/sample_data"
    )
    print()
    
    print("=" * 60)
    print("路网数据生成完成！")
    print("=" * 60)