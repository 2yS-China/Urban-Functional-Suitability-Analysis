"""
数据标准化模块
负责将不同格式、不同坐标系的GIS数据转换为统一标准格式
支持矢量数据（GeoJSON/Shapefile）和栅格数据（TIF/TIFF）
"""

import geopandas as gpd
from shapely.geometry import shape, mapping
from shapely.validation import make_valid
from shapely.ops import transform
from pyproj import Transformer
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple
import logging

logger = logging.getLogger(__name__)


class DataNormalizer:
    """数据标准化器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化标准化器
        
        Args:
            config_path: 字段映射配置文件路径，默认使用同目录下的field_mapping.yaml
        """
        if config_path is None:
            config_path = Path(__file__).parent / "field_mapping.yaml"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.default_crs = self.config['coordinate_systems']['default_output']
        
    def normalize_boundary(
        self,
        data: Union[str, gpd.GeoDataFrame],
        source_type: str = "default"
    ) -> gpd.GeoDataFrame:
        """
        标准化边界数据
        
        Args:
            data: 文件路径或GeoDataFrame
            source_type: 数据源类型（default/geojson/shapefile）
            
        Returns:
            标准化后的GeoDataFrame
        """
        gdf = self._load_geodata(data)
        
        # 坐标系转换
        gdf = self._transform_crs(gdf, self.default_crs)
        
        # 几何修复
        gdf = self._repair_geometry(gdf)
        
        # 字段映射
        gdf = self._map_fields(gdf, 'boundary', source_type)
        
        # 数据验证
        self._validate_data(gdf, 'boundary')
        
        # 计算面积（如果没有）
        if 'area' not in gdf.columns or gdf['area'].isna().any():
            gdf['area'] = gdf.geometry.area
        
        logger.info(f"边界数据标准化完成: {len(gdf)} 个要素")
        return gdf
    
    def normalize_poi(
        self,
        data: Union[str, gpd.GeoDataFrame],
        source_type: str = "default"
    ) -> gpd.GeoDataFrame:
        """
        标准化POI数据
        
        Args:
            data: 文件路径或GeoDataFrame
            source_type: 数据源类型
            
        Returns:
            标准化后的GeoDataFrame
        """
        gdf = self._load_geodata(data)
        
        # 坐标系转换
        gdf = self._transform_crs(gdf, self.default_crs)
        
        # 字段映射
        gdf = self._map_fields(gdf, 'poi', source_type)
        
        # POI类别标准化
        gdf = self._standardize_poi_category(gdf)
        
        # 数据验证
        self._validate_data(gdf, 'poi')
        
        logger.info(f"POI数据标准化完成: {len(gdf)} 个点位")
        return gdf
    
    def normalize_roads(
        self,
        data: Union[str, gpd.GeoDataFrame],
        source_type: str = "default"
    ) -> gpd.GeoDataFrame:
        """
        标准化路网数据
        
        Args:
            data: 文件路径或GeoDataFrame
            source_type: 数据源类型
            
        Returns:
            标准化后的GeoDataFrame
        """
        gdf = self._load_geodata(data)
        
        # 坐标系转换
        gdf = self._transform_crs(gdf, self.default_crs)
        
        # 字段映射
        gdf = self._map_fields(gdf, 'roads', source_type)
        
        # 道路等级标准化
        gdf = self._standardize_road_type(gdf)
        
        # 数据验证
        self._validate_data(gdf, 'roads')
        
        logger.info(f"路网数据标准化完成: {len(gdf)} 条道路")
        return gdf
    
    def normalize_raster(
        self,
        raster_path: str,
        output_path: Optional[str] = None,
        target_crs: Optional[str] = None,
        boundary: Optional[gpd.GeoDataFrame] = None
    ) -> Tuple[str, Dict]:
        """
        标准化栅格数据（TIF/TIFF）
        
        Args:
            raster_path: 栅格文件路径
            output_path: 输出文件路径（可选）
            target_crs: 目标坐标系（可选，默认使用配置中的默认坐标系）
            boundary: 裁剪边界（可选）
            
        Returns:
            (处理后文件路径, 元数据字典)
        """
        try:
            from .raster_processor import RasterProcessor
        except ImportError:
            raise ImportError("栅格处理需要 rasterio 库，请安装: pip install rasterio")
        
        processor = RasterProcessor()
        
        # 如果未指定目标坐标系，使用默认坐标系
        if target_crs is None:
            target_crs = self.default_crs
        
        # 如果未指定输出路径，生成默认路径
        if output_path is None:
            input_path = Path(raster_path)
            output_path = input_path.parent / f"{input_path.stem}_normalized.tif"
        
        # 加载栅格
        data, metadata = processor.load_raster(raster_path)
        current_path = raster_path
        
        # 坐标系转换（如果需要）
        if str(metadata['crs']) != target_crs:
            logger.info(f"栅格坐标系转换: {metadata['crs']} -> {target_crs}")
            temp_path = Path(output_path).parent / f"temp_reprojected.tif"
            data, metadata = processor.reproject_raster(
                current_path, target_crs, output_path=str(temp_path)
            )
            current_path = str(temp_path)
        
        # 边界裁剪（如果提供）
        if boundary is not None:
            logger.info("按边界裁剪栅格")
            data, metadata = processor.clip_by_boundary(
                current_path, boundary, output_path=str(output_path)
            )
        else:
            # 如果没有裁剪，复制到输出路径
            if current_path != str(output_path):
                import shutil
                shutil.copy(current_path, output_path)
        
        logger.info(f"栅格数据标准化完成: {output_path}")
        
        return str(output_path), metadata
    
    def _load_geodata(self, data: Union[str, gpd.GeoDataFrame]) -> gpd.GeoDataFrame:
        """加载地理数据"""
        if isinstance(data, gpd.GeoDataFrame):
            return data.copy()
        
        file_path = Path(data)
        
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 根据后缀判断格式
        suffix = file_path.suffix.lower()
        
        if suffix == '.geojson' or suffix == '.json':
            gdf = gpd.read_file(file_path, driver='GeoJSON')
        elif suffix == '.shp':
            gdf = gpd.read_file(file_path)
        elif suffix == '.zip':
            # ZIP压缩的Shapefile
            gdf = gpd.read_file(f"zip://{file_path}")
        else:
            # 尝试自动识别
            gdf = gpd.read_file(file_path)
        
        return gdf
    
    def _transform_crs(
        self,
        gdf: gpd.GeoDataFrame,
        target_crs: str
    ) -> gpd.GeoDataFrame:
        """坐标系转换"""
        if gdf.crs is None:
            logger.warning("数据没有坐标系信息，假定为WGS84")
            gdf = gdf.set_crs('EPSG:4326')
        
        if gdf.crs.to_string() != target_crs:
            logger.info(f"坐标系转换: {gdf.crs} -> {target_crs}")
            gdf = gdf.to_crs(target_crs)
        
        return gdf
    
    def _repair_geometry(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """修复几何"""
        invalid_count = (~gdf.geometry.is_valid).sum()
        
        if invalid_count > 0:
            logger.warning(f"检测到 {invalid_count} 个无效几何，正在修复...")
            gdf['geometry'] = gdf.geometry.apply(lambda geom: make_valid(geom) if not geom.is_valid else geom)
        
        return gdf
    
    def _map_fields(
        self,
        gdf: gpd.GeoDataFrame,
        data_type: str,
        source_type: str
    ) -> gpd.GeoDataFrame:
        """字段映射"""
        mapping_config = self.config[data_type]['source_mappings'][source_type]
        standard_fields = self.config[data_type]['standard_fields']
        
        # 提取标准字段名
        std_field_names = [list(field.keys())[0] for field in standard_fields]
        
        mapped_data = {}
        mapped_data['geometry'] = gdf.geometry
        
        for std_field in std_field_names:
            if std_field == 'geometry':
                continue
                
            possible_names = mapping_config.get(std_field, [])
            if isinstance(possible_names, str):
                possible_names = [possible_names]
            
            # 尝试找到匹配的字段
            found = False
            for col in gdf.columns:
                if col in possible_names:
                    mapped_data[std_field] = gdf[col]
                    found = True
                    break
            
            if not found:
                # 如果找不到，尝试大小写不敏感匹配
                col_lower = {c.lower(): c for c in gdf.columns}
                for name in possible_names:
                    if name.lower() in col_lower:
                        mapped_data[std_field] = gdf[col_lower[name.lower()]]
                        found = True
                        break
            
            if not found:
                logger.warning(f"未找到字段 '{std_field}' 的映射，将设置为空值")
                mapped_data[std_field] = None
        
        result = gpd.GeoDataFrame(mapped_data, crs=gdf.crs)
        return result
    
    def _standardize_poi_category(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """POI类别标准化"""
        if 'category' not in gdf.columns:
            return gdf
        
        category_mapping = self.config['poi']['category_mapping']
        
        # 构建反向映射：细分类型 -> 标准类别
        reverse_map = {}
        for std_category, subtypes in category_mapping.items():
            for subtype in subtypes:
                reverse_map[subtype] = std_category
        
        # 应用映射
        def map_category(cat):
            if cat is None or cat == '':
                return '其他'
            # 直接匹配
            if cat in reverse_map:
                return reverse_map[cat]
            # 模糊匹配（包含关键词）
            for subtype, std_cat in reverse_map.items():
                if subtype in str(cat):
                    return std_cat
            return '其他'
        
        gdf['category'] = gdf['category'].apply(map_category)
        
        return gdf
    
    def _standardize_road_type(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """道路类型标准化"""
        if 'road_type' not in gdf.columns:
            return gdf
        
        hierarchy = self.config['roads']['road_type_hierarchy']
        
        # 构建反向映射
        reverse_map = {}
        for level, types in hierarchy.items():
            for road_type in types:
                reverse_map[road_type] = int(level)
        
        # 添加等级字段
        def get_level(road_type):
            if road_type is None or road_type == '':
                return 4  # 默认最低等级
            for rtype, level in reverse_map.items():
                if rtype in str(road_type):
                    return level
            return 4
        
        gdf['road_level'] = gdf['road_type'].apply(get_level)
        
        return gdf
    
    def _validate_data(self, gdf: gpd.GeoDataFrame, data_type: str):
        """数据验证"""
        rules = self.config['validation_rules'][data_type]
        
        # 几何类型验证
        expected_types = rules['geometry_type']
        actual_types = gdf.geometry.geom_type.unique()
        
        for geom_type in actual_types:
            if geom_type not in expected_types:
                logger.warning(f"检测到非预期几何类型: {geom_type}，预期: {expected_types}")
        
        # 特定验证
        if data_type == 'boundary':
            # 面积验证
            min_area = rules.get('min_area', 0)
            max_area = rules.get('max_area', float('inf'))
            
            invalid_area = gdf[(gdf.geometry.area < min_area) | (gdf.geometry.area > max_area)]
            if len(invalid_area) > 0:
                logger.warning(f"{len(invalid_area)} 个要素面积超出合理范围")
        
        elif data_type == 'poi':
            # 必填字段验证
            required = rules.get('required_fields', [])
            for field in required:
                if field in gdf.columns:
                    null_count = gdf[field].isna().sum()
                    if null_count > 0:
                        logger.warning(f"必填字段 '{field}' 有 {null_count} 个空值")
        
        logger.info(f"{data_type} 数据验证完成")


# 便捷函数
def normalize_data(
    file_path: str,
    data_type: str,
    source_type: str = "default",
    config_path: Optional[str] = None
) -> gpd.GeoDataFrame:
    """
    便捷函数：标准化数据
    
    Args:
        file_path: 数据文件路径
        data_type: 数据类型（boundary/poi/roads）
        source_type: 数据源类型
        config_path: 配置文件路径
        
    Returns:
        标准化后的GeoDataFrame
    """
    normalizer = DataNormalizer(config_path)
    
    if data_type == 'boundary':
        return normalizer.normalize_boundary(file_path, source_type)
    elif data_type == 'poi':
        return normalizer.normalize_poi(file_path, source_type)
    elif data_type == 'roads':
        return normalizer.normalize_roads(file_path, source_type)
    else:
        raise ValueError(f"不支持的数据类型: {data_type}")