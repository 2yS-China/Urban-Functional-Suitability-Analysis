"""
矢量约束数据处理模块
处理水体、生态红线、基本农田、建成区、城市中心等约束数据
"""

import geopandas as gpd
import numpy as np
from shapely.geometry import Point
from scipy.spatial import cKDTree
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def process_water_bodies(
    water_path: str,
    units: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """
    处理水体数据，计算距离和临水性
    
    Args:
        water_path: 水体矢量数据路径
        units: 分析单元
        
    Returns:
        添加水体相关特征的单元GeoDataFrame
    """
    logger.info("开始处理水体数据...")
    
    water = gpd.read_file(water_path)
    result = units.copy()
    
    # 确保坐标系一致
    if water.crs != result.crs:
        water = water.to_crs(result.crs)
    
    # 计算到最近水体的距离
    distances = []
    proximity_scores = []
    
    for unit_geom in result.geometry:
        centroid = unit_geom.centroid
        
        # 计算到所有水体的最小距离
        min_dist = float('inf')
        for water_geom in water.geometry:
            dist = centroid.distance(water_geom)
            if dist < min_dist:
                min_dist = dist
        
        # 转换为米
        dist_m = min_dist * 111000
        distances.append(dist_m)
        
        # 临水性指数（距离越近得分越高）
        proximity = np.exp(-dist_m / 500)  # 500m衰减系数
        proximity_scores.append(proximity)
    
    result['dist_to_water'] = distances
    result['water_proximity'] = proximity_scores
    
    logger.info(f"水体数据处理完成，平均距离: {np.mean(distances):.1f}米")
    return result


def process_ecological_redline(
    redline_path: str,
    units: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """
    处理生态保护红线
    
    Args:
        redline_path: 生态红线矢量数据路径
        units: 分析单元
        
    Returns:
        添加生态红线特征的单元GeoDataFrame
    """
    logger.info("开始处理生态保护红线...")
    
    redline = gpd.read_file(redline_path)
    result = units.copy()
    
    if redline.crs != result.crs:
        redline = redline.to_crs(result.crs)
    
    # 判断是否在生态红线内
    in_redline = []
    dist_to_redline = []
    
    for unit_geom in result.geometry:
        centroid = unit_geom.centroid
        
        # 检查是否与生态红线相交
        intersects = any(unit_geom.intersects(r) for r in redline.geometry)
        in_redline.append(1 if intersects else 0)
        
        # 如果不在红线内，计算距离
        if not intersects:
            min_dist = float('inf')
            for red_geom in redline.geometry:
                dist = centroid.distance(red_geom)
                if dist < min_dist:
                    min_dist = dist
            dist_to_redline.append(min_dist * 111000)
        else:
            dist_to_redline.append(0.0)
    
    result['in_ecological_redline'] = in_redline
    result['dist_to_ecological_redline'] = dist_to_redline
    
    # 生态约束强度（在红线内为1，距离越远约束越小）
    result['ecological_constraint'] = result.apply(
        lambda row: 1.0 if row['in_ecological_redline'] == 1 
        else np.exp(-row['dist_to_ecological_redline'] / 1000),
        axis=1
    )
    
    redline_count = sum(in_redline)
    logger.info(f"生态红线处理完成，{redline_count}个单元在红线内")
    return result


def process_farmland_protection(
    farmland_path: str,
    units: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """
    处理基本农田保护区
    
    Args:
        farmland_path: 基本农田矢量数据路径
        units: 分析单元
        
    Returns:
        添加基本农田特征的单元GeoDataFrame
    """
    logger.info("开始处理基本农田保护区...")
    
    farmland = gpd.read_file(farmland_path)
    result = units.copy()
    
    if farmland.crs != result.crs:
        farmland = farmland.to_crs(result.crs)
    
    in_farmland = []
    dist_to_farmland = []
    
    for unit_geom in result.geometry:
        centroid = unit_geom.centroid
        
        # 检查是否与基本农田相交
        intersects = any(unit_geom.intersects(f) for f in farmland.geometry)
        in_farmland.append(1 if intersects else 0)
        
        if not intersects:
            min_dist = float('inf')
            for farm_geom in farmland.geometry:
                dist = centroid.distance(farm_geom)
                if dist < min_dist:
                    min_dist = dist
            dist_to_farmland.append(min_dist * 111000)
        else:
            dist_to_farmland.append(0.0)
    
    result['in_farmland_protection'] = in_farmland
    result['dist_to_farmland'] = dist_to_farmland
    
    # 农田约束强度
    result['farmland_constraint'] = result.apply(
        lambda row: 1.0 if row['in_farmland_protection'] == 1
        else np.exp(-row['dist_to_farmland'] / 800),
        axis=1
    )
    
    farmland_count = sum(in_farmland)
    logger.info(f"基本农田处理完成，{farmland_count}个单元在保护区内")
    return result


def process_built_area(
    built_path: str,
    units: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """
    处理建成区范围
    
    Args:
        built_path: 建成区矢量数据路径
        units: 分析单元
        
    Returns:
        添加建成区特征的单元GeoDataFrame
    """
    logger.info("开始处理建成区范围...")
    
    built = gpd.read_file(built_path)
    result = units.copy()
    
    if built.crs != result.crs:
        built = built.to_crs(result.crs)
    
    in_built = []
    dist_to_built_edge = []
    
    for unit_geom in result.geometry:
        centroid = unit_geom.centroid
        
        # 检查是否在建成区内
        is_in = any(centroid.within(b) for b in built.geometry)
        in_built.append(1 if is_in else 0)
        
        # 计算到建成区边界的距离
        if is_in:
            # 在建成区内，计算到边界的距离
            min_dist_to_edge = float('inf')
            for built_geom in built.geometry:
                if centroid.within(built_geom):
                    dist = centroid.distance(built_geom.boundary)
                    if dist < min_dist_to_edge:
                        min_dist_to_edge = dist
            dist_to_built_edge.append(-min_dist_to_edge * 111000)  # 负值表示在内部
        else:
            # 在建成区外，计算到边界的距离
            min_dist = float('inf')
            for built_geom in built.geometry:
                dist = centroid.distance(built_geom)
                if dist < min_dist:
                    min_dist = dist
            dist_to_built_edge.append(min_dist * 111000)  # 正值表示在外部
    
    result['in_built_area'] = in_built
    result['dist_to_built_edge'] = dist_to_built_edge
    
    # 建成区缓冲带等级（0-1-2-3：远郊-近郊-边缘-核心）
    result['built_buffer_zone'] = result['dist_to_built_edge'].apply(
        lambda d: 3 if d < 0 else  # 核心区（内部）
                  2 if d < 500 else  # 边缘区（500m内）
                  1 if d < 2000 else  # 近郊（2km内）
                  0  # 远郊（2km外）
    )
    
    built_count = sum(in_built)
    logger.info(f"建成区处理完成，{built_count}个单元在建成区内")
    return result


def process_city_center(
    center_path: str,
    units: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """
    处理城市中心点，计算中心辐射强度
    
    Args:
        center_path: 城市中心点数据路径
        units: 分析单元
        
    Returns:
        添加城市中心特征的单元GeoDataFrame
    """
    logger.info("开始处理城市中心...")
    
    centers = gpd.read_file(center_path)
    result = units.copy()
    
    if centers.crs != result.crs:
        centers = centers.to_crs(result.crs)
    
    # 如果有重要性等级，使用它；否则默认为1
    if 'importance' in centers.columns:
        importance_weights = centers['importance'].values
    else:
        importance_weights = np.ones(len(centers))
    
    # 计算到各中心的加权距离
    radiation_intensities = []
    min_dist_to_center = []
    
    for unit_geom in result.geometry:
        centroid = unit_geom.centroid
        
        # 计算到所有中心的距离
        distances = []
        for center_geom in centers.geometry:
            dist = centroid.distance(center_geom) * 111000  # 转米
            distances.append(dist)
        
        min_dist_to_center.append(min(distances))
        
        # 计算综合辐射强度（多中心叠加，考虑重要性权重）
        total_radiation = 0.0
        for dist, weight in zip(distances, importance_weights):
            # 辐射强度随距离衰减（指数模型）
            radiation = weight * np.exp(-dist / 5000)  # 5km衰减系数
            total_radiation += radiation
        
        radiation_intensities.append(total_radiation)
    
    result['dist_to_city_center'] = min_dist_to_center
    result['city_center_radiation'] = radiation_intensities
    
    # 归一化辐射强度（0-1）
    max_radiation = max(radiation_intensities)
    if max_radiation > 0:
        result['city_center_radiation_normalized'] = result['city_center_radiation'] / max_radiation
    else:
        result['city_center_radiation_normalized'] = 0.5
    
    logger.info(f"城市中心处理完成，平均距离: {np.mean(min_dist_to_center):.1f}米")
    return result


# 便捷函数：批量处理所有约束数据
def process_all_constraints(
    units: gpd.GeoDataFrame,
    water_path: Optional[str] = None,
    redline_path: Optional[str] = None,
    farmland_path: Optional[str] = None,
    built_path: Optional[str] = None,
    center_path: Optional[str] = None
) -> gpd.GeoDataFrame:
    """
    批量处理所有矢量约束数据
    
    Args:
        units: 分析单元
        water_path: 水体数据路径
        redline_path: 生态红线数据路径
        farmland_path: 基本农田数据路径
        built_path: 建成区数据路径
        center_path: 城市中心数据路径
        
    Returns:
        添加所有约束特征的单元GeoDataFrame
    """
    result = units.copy()
    
    if water_path:
        result = process_water_bodies(water_path, result)
    
    if redline_path:
        result = process_ecological_redline(redline_path, result)
    
    if farmland_path:
        result = process_farmland_protection(farmland_path, result)
    
    if built_path:
        result = process_built_area(built_path, result)
    
    if center_path:
        result = process_city_center(center_path, result)
    
    logger.info("所有约束数据处理完成")
    return result