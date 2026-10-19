"""
生成示例POI数据
模拟真实城市的兴趣点分布
"""

import geopandas as gpd
from shapely.geometry import Point
import numpy as np
import json
from pathlib import Path
from typing import Tuple

# POI类别配置
POI_CATEGORIES = {
    '交通设施': {
        'subtypes': ['地铁站', '公交站'],
        'density': 'low',  # 每平方公里数量级
        'distribution': 'grid'  # 分布模式：grid(网格), cluster(聚集), random(随机)
    },
    '商业服务': {
        'subtypes': ['购物中心', '超市', '便利店', '餐饮'],
        'density': 'high',
        'distribution': 'cluster'
    },
    '公共服务': {
        'subtypes': ['学校', '医院', '社区服务中心'],
        'density': 'medium',
        'distribution': 'grid'
    },
    '绿地公园': {
        'subtypes': ['公园', '广场'],
        'density': 'low',
        'distribution': 'random'
    },
    '办公场所': {
        'subtypes': ['写字楼', '商务中心'],
        'density': 'medium',
        'distribution': 'cluster'
    }
}

DENSITY_COUNTS = {
    'low': 5,      # 5个/km²
    'medium': 15,  # 15个/km²
    'high': 30     # 30个/km²
}


def calculate_poi_count(area_km2: float, density: str) -> int:
    """根据面积和密度计算POI数量"""
    base_count = DENSITY_COUNTS[density]
    return int(area_km2 * base_count)


def generate_grid_distribution(
    bounds: Tuple[float, float, float, float],
    count: int
) -> list:
    """生成网格分布的点位"""
    minx, miny, maxx, maxy = bounds
    
    # 计算网格尺寸
    grid_size = int(np.ceil(np.sqrt(count)))
    
    x_coords = np.linspace(minx, maxx, grid_size)
    y_coords = np.linspace(miny, maxy, grid_size)
    
    points = []
    for x in x_coords:
        for y in y_coords:
            if len(points) >= count:
                break
            # 添加小扰动，避免完全对齐
            jitter_x = (np.random.random() - 0.5) * (maxx - minx) / grid_size * 0.3
            jitter_y = (np.random.random() - 0.5) * (maxy - miny) / grid_size * 0.3
            points.append((x + jitter_x, y + jitter_y))
        if len(points) >= count:
            break
    
    return points[:count]


def generate_cluster_distribution(
    bounds: Tuple[float, float, float, float],
    count: int,
    num_clusters: int = None
) -> list:
    """生成聚集分布的点位"""
    minx, miny, maxx, maxy = bounds
    
    if num_clusters is None:
        num_clusters = max(2, count // 5)  # 默认每簇5个点
    
    # 生成聚类中心
    cluster_centers = [
        (
            np.random.uniform(minx, maxx),
            np.random.uniform(miny, maxy)
        )
        for _ in range(num_clusters)
    ]
    
    # 生成点位
    points = []
    cluster_std = min(maxx - minx, maxy - miny) * 0.05  # 聚类标准差
    
    for i in range(count):
        center = cluster_centers[i % num_clusters]
        x = np.random.normal(center[0], cluster_std)
        y = np.random.normal(center[1], cluster_std)
        
        # 确保在边界内
        x = np.clip(x, minx, maxx)
        y = np.clip(y, miny, maxy)
        
        points.append((x, y))
    
    return points


def generate_random_distribution(
    bounds: Tuple[float, float, float, float],
    count: int
) -> list:
    """生成随机分布的点位"""
    minx, miny, maxx, maxy = bounds
    
    points = [
        (
            np.random.uniform(minx, maxx),
            np.random.uniform(miny, maxy)
        )
        for _ in range(count)
    ]
    
    return points


def generate_pois_for_boundary(
    boundary_file: str,
    output_dir: str = "backend/sample_data",
    seed: int = 42
) -> Tuple[gpd.GeoDataFrame, str]:
    """
    为给定边界生成POI数据（带地铁线路等扩展信息）
    
    Args:
        boundary_file: 边界文件路径
        output_dir: 输出目录
        seed: 随机种子
        
    Returns:
        (POI的GeoDataFrame, 输出文件路径)
    """
    np.random.seed(seed)
    
    # 地铁线路配置
    METRO_LINES = {
        'L1': {'name': '1号线', 'key_areas': ['CBD', '火车站', '机场']},
        'L2': {'name': '2号线', 'key_areas': ['CBD', '高新区', '大学城']},
        'L3': {'name': '3号线', 'key_areas': ['高新区', '医院', '体育中心']}
    }
    
    # 读取边界
    boundary = gpd.read_file(boundary_file)
    bounds = boundary.total_bounds  # (minx, miny, maxx, maxy)
    
    # 计算面积（平方公里）
    # 对于WGS84，粗略估算
    area_km2 = boundary.geometry.area.sum() * 111 * 85  # 经纬度转km^2
    
    print(f"边界面积: {area_km2:.2f} km^2")
    
    # 生成所有POI
    all_pois = []
    metro_station_count = 0
    
    for category, config in POI_CATEGORIES.items():
        density = config['density']
        distribution = config['distribution']
        subtypes = config['subtypes']
        
        # 计算该类别POI总数
        total_count = calculate_poi_count(area_km2, density)
        
        print(f"  {category}: {total_count} 个 ({distribution}分布)")
        
        # 生成坐标
        if distribution == 'grid':
            coords = generate_grid_distribution(bounds, total_count)
        elif distribution == 'cluster':
            coords = generate_cluster_distribution(bounds, total_count)
        else:  # random
            coords = generate_random_distribution(bounds, total_count)
        
        # 为每个点分配子类型
        for i, (x, y) in enumerate(coords):
            subtype = subtypes[i % len(subtypes)]
            
            poi_data = {
                'category': category,
                'type': subtype,
                'name': f"{subtype}{i+1:03d}",
                'geometry': Point(x, y)
            }
            
            # 为地铁站添加线路信息
            if subtype == '地铁站':
                metro_line = list(METRO_LINES.keys())[metro_station_count % len(METRO_LINES)]
                poi_data['metro_line'] = metro_line
                poi_data['line_name'] = METRO_LINES[metro_line]['name']
                poi_data['key_areas'] = ','.join(METRO_LINES[metro_line]['key_areas'])
                metro_station_count += 1
            
            all_pois.append(poi_data)
    
    # 创建GeoDataFrame
    poi_gdf = gpd.GeoDataFrame(all_pois, crs='EPSG:4326')
    
    # 保存
    output_path = Path(output_dir)
    output_file = output_path / "sample_poi.geojson"
    poi_gdf.to_file(output_file, driver='GeoJSON')
    
    # 同时保存地铁线路信息
    metro_info_file = output_path / "metro_lines.json"
    with open(metro_info_file, 'w', encoding='utf-8') as f:
        json.dump(METRO_LINES, f, ensure_ascii=False, indent=2)
    
    print(f"\n[OK] 生成POI数据: {output_file}")
    print(f"  - 总数: {len(poi_gdf)} 个POI")
    print(f"  - 类别分布:")
    for cat in poi_gdf['category'].value_counts().items():
        print(f"    - {cat[0]}: {cat[1]}")
    
    if metro_station_count > 0:
        print(f"  - 地铁站: {metro_station_count} 个，分布在{len(METRO_LINES)}条线路")
        print(f"  - 地铁线路信息: {metro_info_file}")
    
    return poi_gdf, str(output_file)


if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    print("=" * 60)
    print("生成示例POI数据")
    print("=" * 60)
    print()
    
    # 检查边界文件是否存在
    boundary_file = "backend/sample_data/sample_boundary.geojson"
    
    if not Path(boundary_file).exists():
        print(f"错误: 边界文件不存在: {boundary_file}")
        print("请先运行 generate_sample_area.py 生成边界数据")
        sys.exit(1)
    
    # 生成POI
    poi_gdf, output_file = generate_pois_for_boundary(
        boundary_file,
        output_dir="backend/sample_data",
        seed=42
    )
    
    print()
    print("=" * 60)
    print("POI数据生成完成！")
    print("=" * 60)