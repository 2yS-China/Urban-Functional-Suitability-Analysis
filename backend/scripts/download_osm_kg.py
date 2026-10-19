"""
从OpenStreetMap下载城市知识图谱数据

使用示例：
    python download_osm_kg.py --city "Beijing" --district "Chaoyang" --output data/beijing_kg.json
"""

import osmnx as ox
import geopandas as gpd
import json
from pathlib import Path
import argparse


def download_osm_knowledge_graph(place_name: str, output_path: str):
    """
    从OSM下载指定地点的知识图谱数据
    
    Args:
        place_name: 地点名称，如 "Chaoyang District, Beijing, China"
        output_path: 输出路径
    """
    print(f"正在下载 {place_name} 的知识图谱数据...")
    
    # 1. 下载POI数据
    print("\n步骤1: 下载POI数据...")
    poi_tags = {
        'amenity': ['school', 'hospital', 'restaurant', 'cafe', 'bank', 
                    'pharmacy', 'police', 'fire_station', 'library', 'parking'],
        'shop': ['supermarket', 'convenience', 'mall', 'department_store'],
        'leisure': ['park', 'garden', 'sports_centre', 'playground'],
        'office': True,
        'tourism': ['hotel', 'museum', 'attraction'],
    }
    
    try:
        pois = ox.geometries_from_place(place_name, poi_tags)
        print(f"  找到 {len(pois)} 个POI")
    except Exception as e:
        print(f"  警告: POI下载失败 - {e}")
        pois = gpd.GeoDataFrame()
    
    # 2. 下载路网数据
    print("\n步骤2: 下载路网数据...")
    try:
        graph = ox.graph_from_place(place_name, network_type='drive')
        nodes, edges = ox.graph_to_gdfs(graph)
        print(f"  找到 {len(nodes)} 个路网节点, {len(edges)} 条道路")
    except Exception as e:
        print(f"  警告: 路网下载失败 - {e}")
        nodes, edges = gpd.GeoDataFrame(), gpd.GeoDataFrame()
    
    # 3. 下载建筑轮廓
    print("\n步骤3: 下载建筑数据...")
    try:
        buildings = ox.geometries_from_place(place_name, {'building': True})
        print(f"  找到 {len(buildings)} 个建筑")
    except Exception as e:
        print(f"  警告: 建筑下载失败 - {e}")
        buildings = gpd.GeoDataFrame()
    
    # 4. 下载边界
    print("\n步骤4: 下载行政边界...")
    try:
        boundary = ox.geocode_to_gdf(place_name)
        print(f"  边界下载成功")
    except Exception as e:
        print(f"  警告: 边界下载失败 - {e}")
        boundary = gpd.GeoDataFrame()
    
    # 5. 构建知识图谱结构
    print("\n步骤5: 构建知识图谱...")
    kg = {
        'metadata': {
            'place': place_name,
            'source': 'OpenStreetMap',
            'nodes_count': 0,
            'relations_count': 0
        },
        'nodes': [],
        'relations': []
    }
    
    node_id = 0
    
    # 添加POI节点
    for idx, poi in pois.iterrows():
        if poi.geometry.geom_type == 'Point':
            kg['nodes'].append({
                'id': f'poi_{node_id}',
                'type': 'poi',
                'properties': {
                    'osm_id': str(idx),
                    'name': poi.get('name', 'Unknown'),
                    'category': poi.get('amenity') or poi.get('shop') or poi.get('leisure', 'other'),
                    'location': {
                        'lon': poi.geometry.x,
                        'lat': poi.geometry.y
                    }
                }
            })
            node_id += 1
    
    # 添加建筑节点（采样，避免过多）
    building_sample = buildings.sample(min(1000, len(buildings))) if len(buildings) > 0 else buildings
    for idx, building in building_sample.iterrows():
        if building.geometry.geom_type == 'Polygon':
            centroid = building.geometry.centroid
            kg['nodes'].append({
                'id': f'building_{node_id}',
                'type': 'building',
                'properties': {
                    'osm_id': str(idx),
                    'building_type': building.get('building', 'yes'),
                    'area': building.geometry.area,
                    'location': {
                        'lon': centroid.x,
                        'lat': centroid.y
                    }
                }
            })
            node_id += 1
    
    # 添加路网节点（采样）
    road_sample = edges.sample(min(500, len(edges))) if len(edges) > 0 else edges
    for idx, road in road_sample.iterrows():
        kg['nodes'].append({
            'id': f'road_{node_id}',
            'type': 'road',
            'properties': {
                'osm_id': str(idx),
                'highway': road.get('highway', 'unknown'),
                'name': road.get('name', 'Unnamed Road'),
                'length': road.get('length', 0)
            }
        })
        node_id += 1
    
    kg['metadata']['nodes_count'] = len(kg['nodes'])
    
    # 保存
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(kg, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ 知识图谱已保存到: {output_path}")
    print(f"  节点数: {kg['metadata']['nodes_count']}")
    print(f"  关系数: {kg['metadata']['relations_count']}")
    
    # 同时保存GeoJSON格式（用于GIS软件查看）
    if len(pois) > 0:
        geojson_path = output_path.parent / f"{output_path.stem}_pois.geojson"
        pois.to_file(geojson_path, driver="GeoJSON")
        print(f"  POI GeoJSON: {geojson_path}")
    
    if len(buildings) > 0:
        geojson_path = output_path.parent / f"{output_path.stem}_buildings.geojson"
        building_sample.to_file(geojson_path, driver="GeoJSON")
        print(f"  建筑 GeoJSON: {geojson_path}")


def main():
    parser = argparse.ArgumentParser(description='从OpenStreetMap下载城市知识图谱')
    parser.add_argument('--place', type=str, default='Chaoyang District, Beijing, China',
                        help='地点名称（英文），如 "Chaoyang District, Beijing, China"')
    parser.add_argument('--output', type=str, default='../sample_data/osm_kg.json',
                        help='输出文件路径')
    
    args = parser.parse_args()
    
    download_osm_knowledge_graph(args.place, args.output)


if __name__ == '__main__':
    main()