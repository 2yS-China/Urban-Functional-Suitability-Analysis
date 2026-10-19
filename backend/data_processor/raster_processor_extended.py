"""
扩展栅格处理模块
处理降水、土壤、GDP、灾害风险等新增栅格数据类型
"""

import rasterio
from rasterio.mask import mask
import geopandas as gpd
import numpy as np
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


def process_precipitation_raster(
    precipitation_path: str,
    units: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """
    处理年降水量栅格
    
    Args:
        precipitation_path: 年降水量栅格路径（单位：毫米）
        units: 分析单元
        
    Returns:
        添加降水特征的单元GeoDataFrame
    """
    logger.info("开始处理年降水量数据...")
    
    with rasterio.open(precipitation_path) as src:
        result = units.copy()
        
        if result.crs != src.crs:
            result = result.to_crs(src.crs)
        
        precipitation_values = []
        
        for zone_geom in result.geometry:
            try:
                out_image, _ = mask(src, [zone_geom], crop=True, all_touched=True)
                data = out_image[0]
                
                if src.nodata is not None:
                    data = data[data != src.nodata]
                
                if len(data) > 0:
                    precipitation_values.append(float(np.mean(data)))
                else:
                    precipitation_values.append(np.nan)
                    
            except Exception as e:
                logger.warning(f"处理降水数据失败: {e}")
                precipitation_values.append(np.nan)
        
        result['annual_precipitation'] = precipitation_values
        
        # 归一化为适宜性指数（800-1200mm为适宜范围）
        result['precipitation_suitability'] = result['annual_precipitation'].apply(
            lambda x: 1.0 if pd.isna(x) else min(1.0, max(0.0, 
                1.0 - abs(x - 1000) / 500))  # 1000mm为最优，±500mm线性衰减
        )
    
    logger.info("年降水量处理完成")
    return result


def process_soil_type_raster(
    soil_path: str,
    units: gpd.GeoDataFrame,
    soil_mapping: Optional[Dict[int, str]] = None
) -> gpd.GeoDataFrame:
    """
    处理土壤类型栅格
    
    Args:
        soil_path: 土壤类型栅格路径
        units: 分析单元
        soil_mapping: 值-土壤类型映射
        
    Returns:
        添加土壤特征的单元GeoDataFrame
    """
    logger.info("开始处理土壤类型数据...")
    
    if soil_mapping is None:
        soil_mapping = {
            1: '砂土',
            2: '壤土',
            3: '粘土',
            4: '有机土',
            5: '盐碱土'
        }
    
    # 土壤适宜性评分（农业/建设）
    soil_suitability = {
        '砂土': {'agriculture': 0.4, 'construction': 0.6},
        '壤土': {'agriculture': 0.9, 'construction': 0.8},
        '粘土': {'agriculture': 0.6, 'construction': 0.5},
        '有机土': {'agriculture': 0.7, 'construction': 0.3},
        '盐碱土': {'agriculture': 0.2, 'construction': 0.4}
    }
    
    with rasterio.open(soil_path) as src:
        result = units.copy()
        
        if result.crs != src.crs:
            result = result.to_crs(src.crs)
        
        soil_types = []
        agri_scores = []
        const_scores = []
        
        for zone_geom in result.geometry:
            try:
                out_image, _ = mask(src, [zone_geom], crop=True, all_touched=True)
                data = out_image[0]
                
                if src.nodata is not None:
                    data = data[data != src.nodata]
                
                if len(data) > 0:
                    # 主导土壤类型
                    unique, counts = np.unique(data, return_counts=True)
                    dominant_value = int(unique[np.argmax(counts)])
                    soil_type = soil_mapping.get(dominant_value, '未知')
                    
                    soil_types.append(soil_type)
                    
                    # 适宜性评分
                    scores = soil_suitability.get(soil_type, {'agriculture': 0.5, 'construction': 0.5})
                    agri_scores.append(scores['agriculture'])
                    const_scores.append(scores['construction'])
                else:
                    soil_types.append('未知')
                    agri_scores.append(0.5)
                    const_scores.append(0.5)
                    
            except Exception as e:
                logger.warning(f"处理土壤数据失败: {e}")
                soil_types.append('未知')
                agri_scores.append(0.5)
                const_scores.append(0.5)
        
        result['soil_type'] = soil_types
        result['soil_agri_suitability'] = agri_scores
        result['soil_const_suitability'] = const_scores
    
    logger.info("土壤类型处理完成")
    return result


def process_gdp_density_raster(
    gdp_path: str,
    units: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """
    处理GDP密度栅格
    
    Args:
        gdp_path: GDP密度栅格路径（单位：万元/km²）
        units: 分析单元
        
    Returns:
        添加GDP特征的单元GeoDataFrame
    """
    logger.info("开始处理GDP密度数据...")
    
    with rasterio.open(gdp_path) as src:
        result = units.copy()
        
        if result.crs != src.crs:
            result = result.to_crs(src.crs)
        
        gdp_values = []
        
        for zone_geom in result.geometry:
            try:
                out_image, _ = mask(src, [zone_geom], crop=True, all_touched=True)
                data = out_image[0]
                
                if src.nodata is not None:
                    data = data[data != src.nodata]
                
                if len(data) > 0:
                    gdp_values.append(float(np.mean(data)))
                else:
                    gdp_values.append(np.nan)
                    
            except Exception as e:
                logger.warning(f"处理GDP数据失败: {e}")
                gdp_values.append(np.nan)
        
        result['gdp_density'] = gdp_values
        
        # 归一化为经济活力指数（0-1）
        if not result['gdp_density'].isna().all():
            max_gdp = result['gdp_density'].max()
            result['economic_vitality'] = result['gdp_density'] / max_gdp if max_gdp > 0 else 0.5
        else:
            result['economic_vitality'] = 0.5
    
    logger.info("GDP密度处理完成")
    return result


def process_flood_risk_raster(
    flood_path: str,
    units: gpd.GeoDataFrame,
    risk_mapping: Optional[Dict[int, str]] = None
) -> gpd.GeoDataFrame:
    """
    处理洪涝灾害风险栅格
    
    Args:
        flood_path: 洪涝风险栅格路径
        units: 分析单元
        risk_mapping: 值-风险等级映射
        
    Returns:
        添加洪涝风险特征的单元GeoDataFrame
    """
    logger.info("开始处理洪涝灾害风险数据...")
    
    if risk_mapping is None:
        risk_mapping = {
            1: '低风险',
            2: '中低风险',
            3: '中风险',
            4: '中高风险',
            5: '高风险'
        }
    
    # 风险评分（数值越小越安全）
    risk_scores = {
        '低风险': 0.9,
        '中低风险': 0.7,
        '中风险': 0.5,
        '中高风险': 0.3,
        '高风险': 0.1
    }
    
    with rasterio.open(flood_path) as src:
        result = units.copy()
        
        if result.crs != src.crs:
            result = result.to_crs(src.crs)
        
        risk_levels = []
        safety_scores = []
        
        for zone_geom in result.geometry:
            try:
                out_image, _ = mask(src, [zone_geom], crop=True, all_touched=True)
                data = out_image[0]
                
                if src.nodata is not None:
                    data = data[data != src.nodata]
                
                if len(data) > 0:
                    # 取最严重风险（最大值）
                    max_risk_value = int(np.max(data))
                    risk_level = risk_mapping.get(max_risk_value, '未知')
                    
                    risk_levels.append(risk_level)
                    safety_scores.append(risk_scores.get(risk_level, 0.5))
                else:
                    risk_levels.append('未知')
                    safety_scores.append(0.5)
                    
            except Exception as e:
                logger.warning(f"处理洪涝风险数据失败: {e}")
                risk_levels.append('未知')
                safety_scores.append(0.5)
        
        result['flood_risk_level'] = risk_levels
        result['flood_safety_score'] = safety_scores
    
    logger.info("洪涝灾害风险处理完成")
    return result


def process_geological_hazard_raster(
    hazard_path: str,
    units: gpd.GeoDataFrame,
    hazard_mapping: Optional[Dict[int, str]] = None
) -> gpd.GeoDataFrame:
    """
    处理地质灾害易发性栅格
    
    Args:
        hazard_path: 地质灾害易发性栅格路径
        units: 分析单元
        hazard_mapping: 值-易发性等级映射
        
    Returns:
        添加地质灾害特征的单元GeoDataFrame
    """
    logger.info("开始处理地质灾害易发性数据...")
    
    if hazard_mapping is None:
        hazard_mapping = {
            1: '不易发',
            2: '低易发',
            3: '中易发',
            4: '高易发',
            5: '极高易发'
        }
    
    # 安全性评分
    safety_scores_map = {
        '不易发': 0.95,
        '低易发': 0.8,
        '中易发': 0.6,
        '高易发': 0.3,
        '极高易发': 0.1
    }
    
    with rasterio.open(hazard_path) as src:
        result = units.copy()
        
        if result.crs != src.crs:
            result = result.to_crs(src.crs)
        
        hazard_levels = []
        safety_scores = []
        
        for zone_geom in result.geometry:
            try:
                out_image, _ = mask(src, [zone_geom], crop=True, all_touched=True)
                data = out_image[0]
                
                if src.nodata is not None:
                    data = data[data != src.nodata]
                
                if len(data) > 0:
                    # 取最严重等级（最大值）
                    max_hazard_value = int(np.max(data))
                    hazard_level = hazard_mapping.get(max_hazard_value, '未知')
                    
                    hazard_levels.append(hazard_level)
                    safety_scores.append(safety_scores_map.get(hazard_level, 0.5))
                else:
                    hazard_levels.append('未知')
                    safety_scores.append(0.5)
                    
            except Exception as e:
                logger.warning(f"处理地质灾害数据失败: {e}")
                hazard_levels.append('未知')
                safety_scores.append(0.5)
        
        result['geological_hazard_level'] = hazard_levels
        result['geological_safety_score'] = safety_scores
    
    logger.info("地质灾害易发性处理完成")
    return result


# 导入pandas用于数据处理
import pandas as pd