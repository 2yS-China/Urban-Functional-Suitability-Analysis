"""
网格划分模块
根据片区边界生成规则网格，或直接使用已有地块作为分析单元
"""

import geopandas as gpd
from shapely.geometry import box, Polygon
from shapely.ops import unary_union
import numpy as np
from typing import Optional, Tuple, Literal
import logging

logger = logging.getLogger(__name__)


class GridGenerator:
    """网格生成器"""
    
    def __init__(self):
        pass
    
    def generate_grid(
        self,
        boundary: gpd.GeoDataFrame,
        grid_size: float = 100.0,
        mode: Literal['square', 'hexagon'] = 'square',
        overlap_threshold: float = 0.5
    ) -> gpd.GeoDataFrame:
        """
        生成规则网格
        
        Args:
            boundary: 边界数据（GeoDataFrame）
            grid_size: 网格大小（米），对于方形网格是边长，六边形是内切圆直径
            mode: 网格类型（square: 方形, hexagon: 六边形）
            overlap_threshold: 与边界重叠比例阈值（0-1），低于此值的网格将被移除
            
        Returns:
            网格GeoDataFrame，包含unit_id和geometry
        """
        # 保存原始CRS
        original_crs = boundary.crs
        
        # 如果是地理坐标系（EPSG:4326），转换为Web墨卡托投影（EPSG:3857，单位：米）
        if boundary.crs and boundary.crs.is_geographic:
            logger.info(f"检测到地理坐标系 {boundary.crs}，转换为 EPSG:3857 进行网格生成")
            boundary_projected = boundary.to_crs("EPSG:3857")
        else:
            boundary_projected = boundary.copy()
        
        # 合并所有边界为单一多边形
        boundary_union = unary_union(boundary_projected.geometry)
        
        if mode == 'square':
            grid_gdf = self._generate_square_grid(
                boundary_union,
                grid_size,
                boundary_projected.crs,
                overlap_threshold
            )
        elif mode == 'hexagon':
            grid_gdf = self._generate_hexagon_grid(
                boundary_union,
                grid_size,
                boundary_projected.crs,
                overlap_threshold
            )
        else:
            raise ValueError(f"不支持的网格类型: {mode}")
        
        # 如果进行了投影转换，转换回原始CRS
        if boundary.crs and boundary.crs.is_geographic:
            grid_gdf = grid_gdf.to_crs(original_crs)
            logger.info(f"网格已转换回原始坐标系 {original_crs}")
        
        # 生成单元ID
        grid_gdf['unit_id'] = [f"UNIT_{i+1:04d}" for i in range(len(grid_gdf))]
        
        # 计算中心点（用于后续分析）
        grid_gdf['centroid_x'] = grid_gdf.geometry.centroid.x
        grid_gdf['centroid_y'] = grid_gdf.geometry.centroid.y
        
        # 计算单元面积
        grid_gdf['area'] = grid_gdf.geometry.area
        
        logger.info(f"生成 {mode} 网格: {len(grid_gdf)} 个单元，网格大小 {grid_size}m")
        
        return grid_gdf
    
    def _generate_square_grid(
        self,
        boundary,
        grid_size: float,
        crs,
        overlap_threshold: float
    ) -> gpd.GeoDataFrame:
        """生成方形网格"""
        # 获取边界范围
        minx, miny, maxx, maxy = boundary.bounds
        
        # 生成网格坐标
        x_coords = np.arange(minx, maxx, grid_size)
        y_coords = np.arange(miny, maxy, grid_size)
        
        logger.info(f"边界范围: ({minx:.2f}, {miny:.2f}) to ({maxx:.2f}, {maxy:.2f})")
        logger.info(f"网格数量: {len(x_coords)} x {len(y_coords)} = {len(x_coords) * len(y_coords)}")
        
        # 创建网格单元
        grid_cells = []
        for x in x_coords:
            for y in y_coords:
                cell = box(x, y, x + grid_size, y + grid_size)
                
                # 计算与边界的交集
                intersection = cell.intersection(boundary)
                
                # 判断重叠比例
                if intersection.area / cell.area >= overlap_threshold:
                    # 使用交集作为实际网格（裁剪到边界内）
                    grid_cells.append(intersection)
        
        logger.info(f"过滤后保留 {len(grid_cells)} 个网格单元（重叠阈值: {overlap_threshold}）")
        
        # 创建GeoDataFrame
        grid_gdf = gpd.GeoDataFrame(geometry=grid_cells, crs=crs)
        
        return grid_gdf
    
    def _generate_hexagon_grid(
        self,
        boundary,
        grid_size: float,
        crs,
        overlap_threshold: float
    ) -> gpd.GeoDataFrame:
        """生成六边形网格"""
        # 六边形的几何参数
        # grid_size 表示内切圆直径
        radius = grid_size / 2  # 内切圆半径
        apothem = radius * np.sqrt(3) / 2  # 边心距
        
        # 六边形宽度和高度
        hex_width = 2 * apothem
        hex_height = 1.5 * radius
        
        # 获取边界范围
        minx, miny, maxx, maxy = boundary.bounds
        
        # 生成六边形坐标
        x_coords = np.arange(minx, maxx + hex_width, hex_width)
        y_coords = np.arange(miny, maxy + hex_height, hex_height)
        
        # 创建六边形单元
        grid_cells = []
        for i, y in enumerate(y_coords):
            for j, x in enumerate(x_coords):
                # 奇数行偏移
                offset_x = apothem if i % 2 == 1 else 0
                center_x = x + offset_x
                center_y = y
                
                # 创建六边形
                hexagon = self._create_hexagon(center_x, center_y, radius)
                
                # 计算与边界的交集
                intersection = hexagon.intersection(boundary)
                
                if intersection.area / hexagon.area >= overlap_threshold:
                    grid_cells.append(intersection)
        
        logger.info(f"过滤后保留 {len(grid_cells)} 个六边形单元")
        
        # 创建GeoDataFrame
        grid_gdf = gpd.GeoDataFrame(geometry=grid_cells, crs=crs)
        
        return grid_gdf
    
    def _create_hexagon(self, center_x: float, center_y: float, radius: float) -> Polygon:
        """创建正六边形"""
        angles = np.linspace(0, 2 * np.pi, 7)  # 7个点（首尾相同）
        x = center_x + radius * np.cos(angles)
        y = center_y + radius * np.sin(angles)
        coords = list(zip(x, y))
        return Polygon(coords)
    
    def use_parcels_as_units(
        self,
        parcels: gpd.GeoDataFrame,
        id_field: Optional[str] = None
    ) -> gpd.GeoDataFrame:
        """
        使用已有地块作为分析单元
        
        Args:
            parcels: 地块数据（GeoDataFrame）
            id_field: 地块ID字段名，如果为None则自动生成
            
        Returns:
            标准化的单元GeoDataFrame
        """
        result = parcels.copy()
        
        # 生成或使用已有ID
        if id_field and id_field in result.columns:
            result['unit_id'] = result[id_field].astype(str)
        else:
            result['unit_id'] = [f"PARCEL_{i+1:04d}" for i in range(len(result))]
        
        # 计算中心点
        result['centroid_x'] = result.geometry.centroid.x
        result['centroid_y'] = result.geometry.centroid.y
        
        # 计算面积
        if 'area' not in result.columns:
            result['area'] = result.geometry.area
        
        # 保留必要字段
        keep_cols = ['unit_id', 'geometry', 'centroid_x', 'centroid_y', 'area']
        if 'land_use' in result.columns:
            keep_cols.append('land_use')
        
        result = result[keep_cols]
        
        logger.info(f"使用地块作为分析单元: {len(result)} 个地块")
        
        return result
    
    def refine_grid_by_boundary(
        self,
        grid: gpd.GeoDataFrame,
        boundary: gpd.GeoDataFrame,
        buffer_distance: float = 0.0
    ) -> gpd.GeoDataFrame:
        """
        按边界精细化裁剪网格（可选的后处理步骤）
        
        Args:
            grid: 网格数据
            boundary: 边界数据
            buffer_distance: 边界缓冲距离（米），正值向外扩展，负值向内收缩
            
        Returns:
            裁剪后的网格
        """
        boundary_union = unary_union(boundary.geometry)
        
        if buffer_distance != 0:
            boundary_union = boundary_union.buffer(buffer_distance)
        
        # 裁剪网格
        refined = grid.copy()
        refined['geometry'] = refined.geometry.intersection(boundary_union)
        
        # 移除面积过小的单元（可能是裁剪产生的碎片）
        min_area = grid['area'].min() * 0.1  # 保留至少10%原面积的单元
        refined = refined[refined.geometry.area >= min_area]
        
        # 重新计算面积和中心点
        refined['area'] = refined.geometry.area
        refined['centroid_x'] = refined.geometry.centroid.x
        refined['centroid_y'] = refined.geometry.centroid.y
        
        logger.info(f"网格精细化完成: {len(refined)} 个单元")
        
        return refined


# 便捷函数
def generate_analysis_units(
    boundary: gpd.GeoDataFrame,
    mode: Literal['grid', 'parcel'] = 'grid',
    grid_size: float = 100.0,
    grid_type: Literal['square', 'hexagon'] = 'square',
    parcels: Optional[gpd.GeoDataFrame] = None,
    **kwargs
) -> gpd.GeoDataFrame:
    """
    便捷函数：生成分析单元
    
    Args:
        boundary: 边界数据
        mode: 模式（grid: 网格划分, parcel: 使用地块）
        grid_size: 网格大小（仅grid模式）
        grid_type: 网格类型（仅grid模式）
        parcels: 地块数据（仅parcel模式）
        **kwargs: 其他参数
        
    Returns:
        分析单元GeoDataFrame
    """
    generator = GridGenerator()
    
    if mode == 'grid':
        return generator.generate_grid(
            boundary,
            grid_size=grid_size,
            mode=grid_type,
            **kwargs
        )
    elif mode == 'parcel':
        if parcels is None:
            raise ValueError("parcel模式需要提供parcels参数")
        return generator.use_parcels_as_units(parcels, **kwargs)
    else:
        raise ValueError(f"不支持的模式: {mode}")