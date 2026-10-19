"""
生成示例片区边界数据
用于测试和演示
"""

import geopandas as gpd
from shapely.geometry import Polygon
import json
from pathlib import Path

def generate_sample_boundary(output_dir: str = "backend/sample_data"):
    """
    生成一个矩形示例片区边界
    模拟一个典型的城市新区（约2km x 1.5km）
    中心点设置在北京某位置附近
    """
    # 中心点坐标（北京某新区，WGS84）
    center_lon = 116.4074  # 经度
    center_lat = 39.9042   # 纬度
    
    # 片区尺寸（经纬度单位，约2km x 1.5km）
    # 1度纬度约111km，1度经度约85km（北京纬度）
    width_deg = 0.02 / 85 * 2000   # 约2km
    height_deg = 0.015 / 111 * 1500  # 约1.5km
    
    # 创建矩形边界
    minx = center_lon - width_deg / 2
    maxx = center_lon + width_deg / 2
    miny = center_lat - height_deg / 2
    maxy = center_lat + height_deg / 2
    
    boundary_polygon = Polygon([
        (minx, miny),
        (maxx, miny),
        (maxx, maxy),
        (minx, maxy),
        (minx, miny)
    ])
    
    # 创建GeoDataFrame
    gdf = gpd.GeoDataFrame(
        {
            'name': ['测试片区A'],
            'area': [boundary_polygon.area * 111 * 85 * 1000000],  # 转换为平方米
            'description': ['用于系统测试的示例片区边界']
        },
        geometry=[boundary_polygon],
        crs='EPSG:4326'
    )
    
    # 保存为GeoJSON
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    output_file = output_path / "sample_boundary.geojson"
    gdf.to_file(output_file, driver='GeoJSON')
    
    print(f"[OK] 生成边界数据: {output_file}")
    print(f"  - 片区名称: 测试片区A")
    print(f"  - 边界范围: ({minx:.6f}, {miny:.6f}) to ({maxx:.6f}, {maxy:.6f})")
    print(f"  - 面积: {gdf['area'].values[0]:.0f} 平方米")
    
    return gdf, output_file


def generate_complex_boundary(output_dir: str = "backend/sample_data"):
    """
    生成一个不规则形状的片区边界
    模拟真实的城市边界形态
    """
    # 中心点
    center_lon = 116.4074
    center_lat = 39.9042
    
    # 创建不规则多边形（L形）
    coords = [
        (116.400, 39.895),  # 左下
        (116.415, 39.895),  # 右下
        (116.415, 39.905),  # 右中
        (116.408, 39.905),  # 中点
        (116.408, 39.913),  # 上中
        (116.400, 39.913),  # 左上
        (116.400, 39.895),  # 回到起点
    ]
    
    boundary_polygon = Polygon(coords)
    
    # 创建GeoDataFrame
    gdf = gpd.GeoDataFrame(
        {
            'name': ['测试片区B（不规则）'],
            'area': [boundary_polygon.area * 111 * 85 * 1000000],
            'description': ['不规则形状的测试片区']
        },
        geometry=[boundary_polygon],
        crs='EPSG:4326'
    )
    
    # 保存
    output_path = Path(output_dir)
    output_file = output_path / "sample_boundary_complex.geojson"
    gdf.to_file(output_file, driver='GeoJSON')
    
    print(f"[OK] 生成复杂边界数据: {output_file}")
    print(f"  - 片区名称: 测试片区B（不规则）")
    print(f"  - 面积: {gdf['area'].values[0]:.0f} 平方米")
    
    return gdf, output_file


if __name__ == "__main__":
    import sys
    
    # 确保路径正确
    output_dir = "backend/sample_data"
    
    print("=" * 60)
    print("生成示例片区边界数据")
    print("=" * 60)
    print()
    
    # 生成简单边界
    gdf1, file1 = generate_sample_boundary(output_dir)
    print()
    
    # 生成复杂边界
    gdf2, file2 = generate_complex_boundary(output_dir)
    print()
    
    print("=" * 60)
    print("所有边界数据生成完成！")
    print("=" * 60)