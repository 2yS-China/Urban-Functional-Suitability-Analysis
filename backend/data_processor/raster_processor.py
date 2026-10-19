"""
栅格数据处理模块
负责处理TIF等栅格格式数据（DEM、遥感影像、土地利用等）
"""

import rasterio
from rasterio.mask import mask
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.features import shapes
import geopandas as gpd
import numpy as np
from shapely.geometry import shape, box
from pathlib import Path
from typing import Union, Optional, Tuple, Dict, List
import logging

logger = logging.getLogger(__name__)


class RasterProcessor:
    """栅格数据处理器"""
    
    def __init__(self):
        """初始化栅格处理器"""
        self.default_crs = 'EPSG:4326'
    
    def load_raster(
        self,
        file_path: str,
        band: int = 1
    ) -> Tuple[np.ndarray, Dict]:
        """
        加载栅格数据
        
        Args:
            file_path: 栅格文件路径（TIF/TIFF）
            band: 波段索引（从1开始）
            
        Returns:
            (数据数组, 元数据字典)
        """
        with rasterio.open(file_path) as src:
            data = src.read(band)
            metadata = {
                'crs': src.crs,
                'transform': src.transform,
                'width': src.width,
                'height': src.height,
                'nodata': src.nodata,
                'bounds': src.bounds
            }
        
        logger.info(f"栅格数据加载完成: {file_path}")
        logger.info(f"  尺寸: {metadata['width']}x{metadata['height']}")
        logger.info(f"  坐标系: {metadata['crs']}")
        
        return data, metadata
    
    def clip_by_boundary(
        self,
        raster_path: str,
        boundary: Union[gpd.GeoDataFrame, str],
        output_path: Optional[str] = None,
        crop: bool = True
    ) -> Tuple[np.ndarray, Dict]:
        """
        按边界裁剪栅格
        
        Args:
            raster_path: 栅格文件路径
            boundary: 边界GeoDataFrame或文件路径
            output_path: 输出文件路径（可选）
            crop: 是否裁剪到边界最小外接矩形
            
        Returns:
            (裁剪后数据, 元数据)
        """
        # 加载边界
        if isinstance(boundary, str):
            boundary = gpd.read_file(boundary)
        
        with rasterio.open(raster_path) as src:
            # 确保边界坐标系与栅格一致
            if boundary.crs != src.crs:
                boundary = boundary.to_crs(src.crs)
            
            # 裁剪
            geoms = [geom for geom in boundary.geometry]
            out_image, out_transform = mask(src, geoms, crop=crop, all_touched=True)
            
            # 更新元数据
            out_meta = src.meta.copy()
            out_meta.update({
                "driver": "GTiff",
                "height": out_image.shape[1],
                "width": out_image.shape[2],
                "transform": out_transform
            })
            
            # 保存裁剪结果
            if output_path:
                with rasterio.open(output_path, "w", **out_meta) as dest:
                    dest.write(out_image)
                logger.info(f"裁剪栅格已保存: {output_path}")
            
            # 返回第一波段
            data = out_image[0]
            metadata = {
                'crs': src.crs,
                'transform': out_transform,
                'width': data.shape[1],
                'height': data.shape[0],
                'nodata': src.nodata,
                'bounds': rasterio.transform.array_bounds(data.shape[0], data.shape[1], out_transform)
            }
        
        return data, metadata
    
    def reproject_raster(
        self,
        raster_path: str,
        target_crs: str,
        output_path: Optional[str] = None,
        resampling_method: str = 'bilinear'
    ) -> Tuple[np.ndarray, Dict]:
        """
        栅格重投影
        
        Args:
            raster_path: 输入栅格路径
            target_crs: 目标坐标系（如'EPSG:4326'）
            output_path: 输出文件路径
            resampling_method: 重采样方法（nearest/bilinear/cubic等）
            
        Returns:
            (重投影后数据, 元数据)
        """
        resampling_map = {
            'nearest': Resampling.nearest,
            'bilinear': Resampling.bilinear,
            'cubic': Resampling.cubic,
            'average': Resampling.average
        }
        
        with rasterio.open(raster_path) as src:
            # 计算转换参数
            transform, width, height = calculate_default_transform(
                src.crs, target_crs, src.width, src.height, *src.bounds
            )
            
            # 更新元数据
            kwargs = src.meta.copy()
            kwargs.update({
                'crs': target_crs,
                'transform': transform,
                'width': width,
                'height': height
            })
            
            # 重投影
            data = np.empty((height, width), dtype=src.dtypes[0])
            reproject(
                source=rasterio.band(src, 1),
                destination=data,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=transform,
                dst_crs=target_crs,
                resampling=resampling_map.get(resampling_method, Resampling.bilinear)
            )
            
            # 保存
            if output_path:
                with rasterio.open(output_path, 'w', **kwargs) as dst:
                    dst.write(data, 1)
                logger.info(f"重投影栅格已保存: {output_path}")
            
            metadata = {
                'crs': target_crs,
                'transform': transform,
                'width': width,
                'height': height,
                'nodata': src.nodata,
                'bounds': rasterio.transform.array_bounds(height, width, transform)
            }
        
        return data, metadata
    
    def extract_values_at_points(
        self,
        raster_path: str,
        points: gpd.GeoDataFrame,
        band: int = 1
    ) -> np.ndarray:
        """
        提取点位处的栅格值
        
        Args:
            raster_path: 栅格文件路径
            points: 点位GeoDataFrame
            band: 波段索引
            
        Returns:
            点位处的栅格值数组
        """
        with rasterio.open(raster_path) as src:
            # 确保坐标系一致
            if points.crs != src.crs:
                points = points.to_crs(src.crs)
            
            # 提取坐标
            coords = [(geom.x, geom.y) for geom in points.geometry]
            
            # 采样
            values = [val[0] for val in src.sample(coords, indexes=band)]
        
        return np.array(values)
    
    def zonal_statistics(
        self,
        raster_path: str,
        zones: gpd.GeoDataFrame,
        stats: List[str] = ['mean', 'min', 'max', 'std'],
        band: int = 1
    ) -> gpd.GeoDataFrame:
        """
        分区统计（计算每个多边形内的栅格统计值）
        
        Args:
            raster_path: 栅格文件路径
            zones: 分区多边形GeoDataFrame
            stats: 统计指标列表
            band: 波段索引
            
        Returns:
            添加统计字段的GeoDataFrame
        """
        with rasterio.open(raster_path) as src:
            # 确保坐标系一致
            if zones.crs != src.crs:
                zones = zones.to_crs(src.crs)
            
            result = zones.copy()
            
            for idx, zone_geom in enumerate(zones.geometry):
                # 裁剪栅格
                try:
                    out_image, out_transform = mask(
                        src, [zone_geom], crop=True, all_touched=True
                    )
                    data = out_image[band - 1]
                    
                    # 去除nodata值
                    if src.nodata is not None:
                        data = data[data != src.nodata]
                    
                    # 计算统计值
                    if 'mean' in stats:
                        result.loc[idx, 'raster_mean'] = np.mean(data) if len(data) > 0 else np.nan
                    if 'min' in stats:
                        result.loc[idx, 'raster_min'] = np.min(data) if len(data) > 0 else np.nan
                    if 'max' in stats:
                        result.loc[idx, 'raster_max'] = np.max(data) if len(data) > 0 else np.nan
                    if 'std' in stats:
                        result.loc[idx, 'raster_std'] = np.std(data) if len(data) > 0 else np.nan
                    if 'median' in stats:
                        result.loc[idx, 'raster_median'] = np.median(data) if len(data) > 0 else np.nan
                    if 'sum' in stats:
                        result.loc[idx, 'raster_sum'] = np.sum(data) if len(data) > 0 else np.nan
                    
                except ValueError:
                    # 如果多边形不在栅格范围内
                    for stat in stats:
                        result.loc[idx, f'raster_{stat}'] = np.nan
        
        logger.info(f"分区统计完成: {len(zones)} 个区域")
        return result
    
    def raster_to_vector(
        self,
        raster_path: str,
        band: int = 1,
        mask_value: Optional[float] = None
    ) -> gpd.GeoDataFrame:
        """
        栅格矢量化
        
        Args:
            raster_path: 栅格文件路径
            band: 波段索引
            mask_value: 要排除的值（如nodata）
            
        Returns:
            矢量化后的GeoDataFrame
        """
        with rasterio.open(raster_path) as src:
            image = src.read(band)
            
            # 创建掩膜
            if mask_value is not None:
                mask_array = image != mask_value
            else:
                mask_array = None
            
            # 矢量化
            results = (
                {'properties': {'value': v}, 'geometry': s}
                for i, (s, v) in enumerate(
                    shapes(image, mask=mask_array, transform=src.transform)
                )
            )
            
            geoms = list(results)
            
            # 创建GeoDataFrame
            gdf = gpd.GeoDataFrame.from_features(geoms, crs=src.crs)
        
        logger.info(f"栅格矢量化完成: {len(gdf)} 个多边形")
        return gdf
    
    def classify_raster(
        self,
        raster_path: str,
        breaks: List[float],
        labels: Optional[List[str]] = None,
        output_path: Optional[str] = None,
        band: int = 1
    ) -> Tuple[np.ndarray, Dict]:
        """
        栅格分级
        
        Args:
            raster_path: 输入栅格路径
            breaks: 分级断点（升序）
            labels: 分级标签（可选）
            output_path: 输出路径
            band: 波段索引
            
        Returns:
            (分级后数据, 元数据)
        """
        with rasterio.open(raster_path) as src:
            data = src.read(band)
            
            # 分级
            classified = np.digitize(data, breaks)
            
            # 保存
            if output_path:
                meta = src.meta.copy()
                meta.update(dtype=rasterio.uint8, count=1)
                
                with rasterio.open(output_path, 'w', **meta) as dst:
                    dst.write(classified.astype(rasterio.uint8), 1)
                logger.info(f"分级栅格已保存: {output_path}")
            
            metadata = {
                'crs': src.crs,
                'transform': src.transform,
                'width': src.width,
                'height': src.height,
                'breaks': breaks,
                'labels': labels
            }
        
        return classified, metadata
    
    def calculate_slope(
        self,
        dem_path: str,
        output_path: Optional[str] = None,
        unit: str = 'degree'
    ) -> Tuple[np.ndarray, Dict]:
        """
        计算坡度
        
        Args:
            dem_path: DEM文件路径
            output_path: 输出路径
            unit: 单位（degree/percent）
            
        Returns:
            (坡度数据, 元数据)
        """
        with rasterio.open(dem_path) as src:
            dem = src.read(1).astype(float)
            transform = src.transform
            
            # 计算像元大小（假设为正方形）
            pixel_size = transform[0]
            
            # 计算梯度
            gy, gx = np.gradient(dem, pixel_size)
            
            # 计算坡度（弧度）
            slope_rad = np.arctan(np.sqrt(gx**2 + gy**2))
            
            # 单位转换
            if unit == 'degree':
                slope = np.degrees(slope_rad)
            elif unit == 'percent':
                slope = np.tan(slope_rad) * 100
            else:
                raise ValueError(f"不支持的单位: {unit}")
            
            # 保存
            if output_path:
                meta = src.meta.copy()
                meta.update(dtype=rasterio.float32)
                
                with rasterio.open(output_path, 'w', **meta) as dst:
                    dst.write(slope.astype(rasterio.float32), 1)
                logger.info(f"坡度栅格已保存: {output_path}")
            
            metadata = {
                'crs': src.crs,
                'transform': src.transform,
                'width': src.width,
                'height': src.height,
                'unit': unit
            }
        
        return slope, metadata
    
    def calculate_aspect(
        self,
        dem_path: str,
        output_path: Optional[str] = None,
        unit: str = 'degree'
    ) -> Tuple[np.ndarray, Dict]:
        """
        计算坡向（Aspect）
        
        Args:
            dem_path: DEM文件路径
            output_path: 输出路径
            unit: 单位（degree/radian）
            
        Returns:
            (坡向数据, 元数据)
            
        Notes:
            坡向值范围：
            - degree模式: 0-360度（0度=北，90度=东，180度=南，270度=西）
            - radian模式: 0-2π弧度
            - 平坦区域（坡度为0）: 值为-1
        """
        with rasterio.open(dem_path) as src:
            dem = src.read(1).astype(float)
            transform = src.transform
            
            # 计算像元大小（假设为正方形）
            pixel_size = transform[0]
            
            # 计算梯度
            gy, gx = np.gradient(dem, pixel_size)
            
            # 计算坡向（弧度，从东向逆时针）
            aspect_rad = np.arctan2(gy, -gx)
            
            # 转换为地理坐标系（从北向顺时针）
            # arctan2返回[-π, π]，转换为[0, 2π]并调整为从北开始
            aspect_rad = np.pi / 2 - aspect_rad
            aspect_rad = np.where(aspect_rad < 0, aspect_rad + 2 * np.pi, aspect_rad)
            
            # 单位转换
            if unit == 'degree':
                aspect = np.degrees(aspect_rad)
            elif unit == 'radian':
                aspect = aspect_rad
            else:
                raise ValueError(f"不支持的单位: {unit}")
            
            # 平坦区域标记为-1
            slope_rad = np.arctan(np.sqrt(gx**2 + gy**2))
            aspect = np.where(slope_rad < 0.001, -1, aspect)  # 坡度接近0时视为平坦
            
            # 保存
            if output_path:
                meta = src.meta.copy()
                meta.update(dtype=rasterio.float32, nodata=-1)
                
                with rasterio.open(output_path, 'w', **meta) as dst:
                    dst.write(aspect.astype(rasterio.float32), 1)
                logger.info(f"坡向栅格已保存: {output_path}")
            
            metadata = {
                'crs': src.crs,
                'transform': src.transform,
                'width': src.width,
                'height': src.height,
                'unit': unit,
                'nodata': -1
            }
        
        return aspect, metadata
    
    def raster_calculator(
        self,
        expression: str,
        rasters: Dict[str, str],
        output_path: Optional[str] = None,
        nodata: Optional[float] = None
    ) -> Tuple[np.ndarray, Dict]:
        """
        栅格代数运算
        
        Args:
            expression: 计算表达式（使用变量名，如 "a + b * 2"）
            rasters: 变量名到栅格路径的映射，如 {"a": "raster1.tif", "b": "raster2.tif"}
            output_path: 输出路径
            nodata: NoData值
            
        Returns:
            (计算结果, 元数据)
            
        Examples:
            # NDVI计算
            processor.raster_calculator(
                expression="(nir - red) / (nir + red)",
                rasters={"nir": "band4.tif", "red": "band3.tif"},
                output_path="ndvi.tif"
            )
            
            # 热舒适度指数
            processor.raster_calculator(
                expression="0.7*temp + 0.3*humidity - 0.5*wind",
                rasters={"temp": "temp.tif", "humidity": "humid.tif", "wind": "wind.tif"}
            )
        """
        # 加载所有栅格
        data_dict = {}
        reference_meta = None
        
        for var_name, raster_path in rasters.items():
            with rasterio.open(raster_path) as src:
                data = src.read(1).astype(float)
                
                # 使用第一个栅格作为参考
                if reference_meta is None:
                    reference_meta = src.meta.copy()
                
                # 处理nodata
                if src.nodata is not None:
                    data = np.where(data == src.nodata, np.nan, data)
                
                data_dict[var_name] = data
        
        # 准备命名空间（包含numpy函数）
        namespace = {
            **data_dict,
            'np': np,
            'sqrt': np.sqrt,
            'log': np.log,
            'log10': np.log10,
            'exp': np.exp,
            'sin': np.sin,
            'cos': np.cos,
            'tan': np.tan,
            'abs': np.abs,
            'power': np.power,
            'where': np.where,
            'maximum': np.maximum,
            'minimum': np.minimum
        }
        
        # 执行计算
        try:
            result = eval(expression, {"__builtins__": {}}, namespace)
        except Exception as e:
            raise ValueError(f"表达式计算失败: {expression}\n错误: {str(e)}")
        
        # 处理结果中的nan
        if nodata is not None:
            result = np.where(np.isnan(result), nodata, result)
        
        # 保存
        if output_path:
            meta = reference_meta.copy()
            meta.update(dtype=rasterio.float32)
            if nodata is not None:
                meta.update(nodata=nodata)
            
            with rasterio.open(output_path, 'w', **meta) as dst:
                dst.write(result.astype(rasterio.float32), 1)
            logger.info(f"计算结果已保存: {output_path}")
        
        metadata = {
            'crs': reference_meta['crs'],
            'transform': reference_meta['transform'],
            'width': reference_meta['width'],
            'height': reference_meta['height'],
            'expression': expression,
            'nodata': nodata
        }
        
        return result, metadata
    
    def classify_aspect(
        self,
        aspect_data: np.ndarray,
        mode: str = '8_directions'
    ) -> np.ndarray:
        """
        坡向分类（转为离散方向）
        
        Args:
            aspect_data: 坡向数据（度数，0-360）
            mode: 分类模式
                - '4_directions': 4方向（北、东、南、西）
                - '8_directions': 8方向（北、东北、东、东南、南、西南、西、西北）
                - 'sunny_shady': 阴阳坡（向阳坡/背阴坡/半阴半阳坡）
        
        Returns:
            分类后的数组
            
        Notes:
            8方向分类:
            1=北(337.5-22.5), 2=东北(22.5-67.5), 3=东(67.5-112.5), 4=东南(112.5-157.5),
            5=南(157.5-202.5), 6=西南(202.5-247.5), 7=西(247.5-292.5), 8=西北(292.5-337.5)
            0=平坦
        """
        classified = np.zeros_like(aspect_data, dtype=np.uint8)
        
        # 平坦区域
        flat_mask = aspect_data == -1
        classified[flat_mask] = 0
        
        if mode == '8_directions':
            # 8方向分类
            breaks = [22.5, 67.5, 112.5, 157.5, 202.5, 247.5, 292.5, 337.5]
            classified[~flat_mask] = np.digitize(aspect_data[~flat_mask], breaks) + 1
            # 处理0-22.5和337.5-360度（都是北）
            classified = np.where((aspect_data >= 337.5) | (aspect_data < 22.5), 1, classified)
            
        elif mode == '4_directions':
            # 4方向分类: 1=北, 2=东, 3=南, 4=西
            breaks = [45, 135, 225, 315]
            temp = np.digitize(aspect_data[~flat_mask], breaks)
            # 映射到1-4
            mapping = {0: 1, 1: 2, 2: 3, 3: 4, 4: 1}  # 最后一档(>315)也是北
            for old_val, new_val in mapping.items():
                classified = np.where((~flat_mask) & (temp == old_val), new_val, classified)
        
        elif mode == 'sunny_shady':
            # 阴阳坡分类: 1=向阳坡(南向,90-270), 2=背阴坡(北向,270-90), 3=半阴半阳
            # 向阳坡（偏南，90-270度）
            classified = np.where((aspect_data >= 90) & (aspect_data < 270), 1, classified)
            # 背阴坡（偏北）
            classified = np.where((aspect_data < 90) | (aspect_data >= 270), 2, classified)
            # 可以细化为半阴半阳坡（东北、西北）
            classified = np.where(
                ((aspect_data >= 45) & (aspect_data < 90)) | 
                ((aspect_data >= 270) & (aspect_data < 315)),
                3, classified
            )
        
        else:
            raise ValueError(f"不支持的分类模式: {mode}")
        
        return classified


# 便捷函数
def process_dem_for_analysis(
    dem_path: str,
    boundary: gpd.GeoDataFrame,
    units: gpd.GeoDataFrame,
    output_dir: Optional[str] = None,
    include_aspect: bool = True
) -> gpd.GeoDataFrame:
    """
    处理DEM用于适宜性分析
    
    Args:
        dem_path: DEM文件路径
        boundary: 分析区域边界
        units: 分析单元（网格）
        output_dir: 输出目录（可选）
        include_aspect: 是否计算坡向（默认True）
        
    Returns:
        添加地形特征的单元GeoDataFrame
    """
    processor = RasterProcessor()
    
    # 1. 裁剪DEM
    logger.info("裁剪DEM到分析区域...")
    if output_dir:
        clipped_dem = Path(output_dir) / "dem_clipped.tif"
    else:
        clipped_dem = None
    
    dem_data, dem_meta = processor.clip_by_boundary(
        dem_path, boundary, output_path=clipped_dem
    )
    
    # 2. 计算坡度
    logger.info("计算坡度...")
    if output_dir:
        slope_path = Path(output_dir) / "slope.tif"
    else:
        slope_path = None
    
    if clipped_dem:
        slope_data, slope_meta = processor.calculate_slope(
            str(clipped_dem), output_path=slope_path
        )
    else:
        # 临时保存裁剪的DEM
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp:
            tmp_dem = tmp.name
        
        with rasterio.open(tmp_dem, 'w', 
                          driver='GTiff',
                          height=dem_data.shape[0],
                          width=dem_data.shape[1],
                          count=1,
                          dtype=dem_data.dtype,
                          crs=dem_meta['crs'],
                          transform=dem_meta['transform']) as dst:
            dst.write(dem_data, 1)
        
        slope_data, slope_meta = processor.calculate_slope(tmp_dem)
        
        # 清理临时文件
        Path(tmp_dem).unlink()
    
    # 3. 计算坡向（可选）
    aspect_data = None
    aspect_path = None
    if include_aspect:
        logger.info("计算坡向...")
        if output_dir:
            aspect_path = Path(output_dir) / "aspect.tif"
        
        if clipped_dem:
            aspect_data, aspect_meta = processor.calculate_aspect(
                str(clipped_dem), output_path=aspect_path
            )
        else:
            # 使用临时DEM
            with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp:
                tmp_dem = tmp.name
            
            with rasterio.open(tmp_dem, 'w',
                              driver='GTiff',
                              height=dem_data.shape[0],
                              width=dem_data.shape[1],
                              count=1,
                              dtype=dem_data.dtype,
                              crs=dem_meta['crs'],
                              transform=dem_meta['transform']) as dst:
                dst.write(dem_data, 1)
            
            aspect_data, aspect_meta = processor.calculate_aspect(tmp_dem)
            Path(tmp_dem).unlink()
    
    # 4. 分区统计
    logger.info("计算单元地形统计...")
    
    # 保存DEM和坡度到临时文件用于分区统计
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp:
        tmp_dem = tmp.name
    with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp:
        tmp_slope = tmp.name
    
    # 保存DEM
    with rasterio.open(tmp_dem, 'w',
                      driver='GTiff',
                      height=dem_data.shape[0],
                      width=dem_data.shape[1],
                      count=1,
                      dtype=dem_data.dtype,
                      crs=dem_meta['crs'],
                      transform=dem_meta['transform']) as dst:
        dst.write(dem_data, 1)
    
    # 保存坡度
    with rasterio.open(tmp_slope, 'w',
                      driver='GTiff',
                      height=slope_data.shape[0],
                      width=slope_data.shape[1],
                      count=1,
                      dtype=slope_data.dtype,
                      crs=slope_meta['crs'],
                      transform=slope_meta['transform']) as dst:
        dst.write(slope_data, 1)
    
    # 高程统计
    result = processor.zonal_statistics(
        tmp_dem, units, stats=['mean', 'min', 'max'], band=1
    )
    result.rename(columns={
        'raster_mean': 'elevation_mean',
        'raster_min': 'elevation_min',
        'raster_max': 'elevation_max'
    }, inplace=True)
    
    # 坡度统计
    slope_stats = processor.zonal_statistics(
        tmp_slope, units, stats=['mean', 'max'], band=1
    )
    result['slope_mean'] = slope_stats['raster_mean']
    result['slope_max'] = slope_stats['raster_max']
    
    # 坡向统计（如果计算了坡向）
    if include_aspect and aspect_data is not None:
        # 保存坡向到临时文件
        with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp:
            tmp_aspect = tmp.name
        
        with rasterio.open(tmp_aspect, 'w',
                          driver='GTiff',
                          height=aspect_data.shape[0],
                          width=aspect_data.shape[1],
                          count=1,
                          dtype=aspect_data.dtype,
                          crs=aspect_meta['crs'],
                          transform=aspect_meta['transform'],
                          nodata=-1) as dst:
            dst.write(aspect_data, 1)
        
        # 坡向统计（平均值，排除平坦区域）
        aspect_stats = processor.zonal_statistics(
            tmp_aspect, units, stats=['mean'], band=1
        )
        result['aspect_mean'] = aspect_stats['raster_mean']
        
        # 坡向分类（主导方向）
        # 对每个单元，统计8个方向的像元数，选择最多的
        aspect_classified = processor.classify_aspect(aspect_data, mode='8_directions')
        
        # 保存分类后的坡向
        with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp:
            tmp_aspect_class = tmp.name
        
        with rasterio.open(tmp_aspect_class, 'w',
                          driver='GTiff',
                          height=aspect_classified.shape[0],
                          width=aspect_classified.shape[1],
                          count=1,
                          dtype=aspect_classified.dtype,
                          crs=aspect_meta['crs'],
                          transform=aspect_meta['transform']) as dst:
            dst.write(aspect_classified, 1)
        
        # 计算主导坡向（众数）
        direction_names = {
            0: '平坦', 1: '北', 2: '东北', 3: '东', 4: '东南',
            5: '南', 6: '西南', 7: '西', 8: '西北'
        }
        
        for idx, zone_geom in enumerate(units.geometry):
            try:
                from rasterio.mask import mask as rasterio_mask
                with rasterio.open(tmp_aspect_class) as src:
                    out_image, _ = rasterio_mask(src, [zone_geom], crop=True, all_touched=True)
                    data = out_image[0]
                    data = data[data != src.nodata] if src.nodata is not None else data
                    
                    if len(data) > 0:
                        # 找出众数（主导方向）
                        unique, counts = np.unique(data, return_counts=True)
                        dominant_value = unique[np.argmax(counts)]
                        result.loc[idx, 'aspect_dominant'] = direction_names.get(int(dominant_value), '未知')
            except Exception:
                result.loc[idx, 'aspect_dominant'] = '未知'
        
        # 清理坡向临时文件
        Path(tmp_aspect).unlink()
        Path(tmp_aspect_class).unlink()
    
    # 清理临时文件
    Path(tmp_dem).unlink()
    Path(tmp_slope).unlink()
    
    logger.info("DEM处理完成")
    return result


def process_landuse_raster(
    landuse_path: str,
    units: gpd.GeoDataFrame,
    landuse_mapping: Optional[Dict[int, str]] = None
) -> gpd.GeoDataFrame:
    """
    处理土地利用栅格
    
    Args:
        landuse_path: 土地利用栅格路径
        units: 分析单元
        landuse_mapping: 值-类别映射字典（可选）
        
    Returns:
        添加土地利用特征的单元GeoDataFrame
    """
    processor = RasterProcessor()
    
    # 默认土地利用映射
    if landuse_mapping is None:
        landuse_mapping = {
            1: '耕地',
            2: '林地',
            3: '草地',
            4: '水域',
            5: '建设用地',
            6: '未利用地'
        }
    
    with rasterio.open(landuse_path) as src:
        result = units.copy()
        
        # 确保坐标系一致
        if result.crs != src.crs:
            result = result.to_crs(src.crs)
        
        # 对每个单元统计土地利用类型占比
        for idx, zone_geom in enumerate(result.geometry):
            try:
                out_image, out_transform = mask(
                    src, [zone_geom], crop=True, all_touched=True
                )
                data = out_image[0]
                
                # 去除nodata
                if src.nodata is not None:
                    data = data[data != src.nodata]
                
                if len(data) == 0:
                    continue
                
                # 统计各类型占比
                unique, counts = np.unique(data, return_counts=True)
                total_pixels = len(data)
                
                for value, count in zip(unique, counts):
                    if value in landuse_mapping:
                        col_name = f'landuse_{landuse_mapping[value]}_ratio'
                        result.loc[idx, col_name] = count / total_pixels
                
                # 主导土地利用类型
                dominant_value = unique[np.argmax(counts)]
                if dominant_value in landuse_mapping:
                    result.loc[idx, 'landuse_dominant'] = landuse_mapping[dominant_value]
                
            except ValueError:
                continue
    
    logger.info("土地利用栅格处理完成")
    return result
