# 栅格数据处理指南

## 概述

数据处理模块现已支持栅格数据（TIF/TIFF 格式），包括：
- DEM（数字高程模型）
- 土地利用/土地覆盖
- NDVI（归一化植被指数）
- 地表温度
- 遥感影像

## 核心功能

### 1. 栅格处理器（RasterProcessor）

位置：`backend/data_processor/raster_processor.py`

#### 主要方法

**加载栅格**
```python
from backend.data_processor.raster_processor import RasterProcessor

processor = RasterProcessor()
data, metadata = processor.load_raster('path/to/raster.tif', band=1)
```

**按边界裁剪**
```python
clipped_data, metadata = processor.clip_by_boundary(
    raster_path='dem.tif',
    boundary=boundary_gdf,  # GeoDataFrame
    output_path='clipped_dem.tif',
    crop=True
)
```

**坐标系重投影**
```python
reprojected_data, metadata = processor.reproject_raster(
    raster_path='input.tif',
    target_crs='EPSG:4326',
    output_path='reprojected.tif',
    resampling_method='bilinear'  # nearest/bilinear/cubic/average
)
```

**提取点位值**
```python
values = processor.extract_values_at_points(
    raster_path='dem.tif',
    points=poi_gdf,
    band=1
)
```

**分区统计**
```python
result = processor.zonal_statistics(
    raster_path='dem.tif',
    zones=grid_gdf,
    stats=['mean', 'min', 'max', 'std', 'median'],
    band=1
)
# 结果：zones 添加 raster_mean, raster_min, raster_max 等列
```

**栅格矢量化**
```python
vector_gdf = processor.raster_to_vector(
    raster_path='landuse.tif',
    band=1,
    mask_value=0  # 排除的值
)
```

**计算坡度**
```python
slope_data, metadata = processor.calculate_slope(
    dem_path='dem.tif',
    output_path='slope.tif',
    unit='degree'  # 或 'percent'
)
```

**计算坡向（新增）**
```python
aspect_data, metadata = processor.calculate_aspect(
    dem_path='dem.tif',
    output_path='aspect.tif',
    unit='degree'  # 或 'radian'
)
# 坡向值范围：
# - degree模式: 0-360度（0度=北，90度=东，180度=南，270度=西）
# - 平坦区域（坡度≈0）: 值为-1
```

**坡向分类（新增）**
```python
# 8方向分类
aspect_classified = processor.classify_aspect(
    aspect_data,
    mode='8_directions'  # 北、东北、东、东南、南、西南、西、西北
)

# 4方向分类
aspect_classified = processor.classify_aspect(
    aspect_data,
    mode='4_directions'  # 北、东、南、西
)

# 阴阳坡分类
aspect_classified = processor.classify_aspect(
    aspect_data,
    mode='sunny_shady'  # 向阳坡(南向)/背阴坡(北向)/半阴半阳
)
```

**栅格代数运算（新增）**
```python
# NDVI 计算
result, metadata = processor.raster_calculator(
    expression="(nir - red) / (nir + red)",
    rasters={"nir": "band4.tif", "red": "band3.tif"},
    output_path="ndvi.tif",
    nodata=-9999
)

# 复合指数计算
result, metadata = processor.raster_calculator(
    expression="0.7*temp + 0.3*humidity - 0.5*wind",
    rasters={
        "temp": "temp.tif",
        "humidity": "humid.tif",
        "wind": "wind.tif"
    },
    output_path="comfort_index.tif"
)

# 条件运算
result, metadata = processor.raster_calculator(
    expression="where(slope < 5, 1, 0)",  # 坡度<5度标记为1
    rasters={"slope": "slope.tif"},
    output_path="flat_areas.tif"
)

# 支持的数学函数：
# np.sqrt, np.log, np.log10, np.exp, np.sin, np.cos, np.tan,
# np.abs, np.power, np.where, np.maximum, np.minimum
```

### 2. DEM 处理流程

一键处理 DEM 用于适宜性分析（含坡向）：

```python
from backend.data_processor.raster_processor import process_dem_for_analysis

result = process_dem_for_analysis(
    dem_path='dem.tif',
    boundary=boundary_gdf,
    units=grid_gdf,  # 分析单元网格
    output_dir='output/',
    include_aspect=True  # 是否计算坡向（默认True）
)

# 结果包含以下字段：
# - elevation_mean: 平均高程
# - elevation_min: 最低高程
# - elevation_max: 最高高程
# - slope_mean: 平均坡度
# - slope_max: 最大坡度
# - aspect_mean: 平均坡向（度数）
# - aspect_dominant: 主导坡向（北/东北/东/东南/南/西南/西/西北/平坦）
```

输出文件：
- `dem_clipped.tif` - 裁剪后的 DEM
- `slope.tif` - 坡度栅格
- `aspect.tif` - 坡向栅格（如果 include_aspect=True）

### 3. 土地利用处理

```python
from backend.data_processor.raster_processor import process_landuse_raster

result = process_landuse_raster(
    landuse_path='landuse.tif',
    units=grid_gdf,
    landuse_mapping={
        1: '耕地',
        2: '林地',
        3: '草地',
        4: '水域',
        5: '建设用地',
        6: '未利用地'
    }
)

# 结果包含以下字段：
# - landuse_耕地_ratio: 耕地占比
# - landuse_林地_ratio: 林地占比
# - landuse_dominant: 主导土地利用类型
# ...
```

### 4. 标准化器集成

`DataNormalizer` 现已支持栅格数据：

```python
from backend.data_processor.normalizer import DataNormalizer

normalizer = DataNormalizer()

# 标准化栅格（坐标系转换 + 裁剪）
output_path, metadata = normalizer.normalize_raster(
    raster_path='input.tif',
    target_crs='EPSG:4326',
    boundary=boundary_gdf,  # 可选
    output_path='output.tif'
)
```

## 配置

栅格数据类型配置位于 `field_mapping.yaml`:

```yaml
raster:
  types:
    dem:
      description: "数字高程模型"
      unit: "米"
      derived_features:
        - "高程统计（均值、最小值、最大值）"
        - "坡度（度或百分比）"
    
    landuse:
      description: "土地利用/土地覆盖"
      classification:
        1: "耕地"
        2: "林地"
        3: "草地"
        4: "水域"
        5: "建设用地"
        6: "未利用地"
```

## 测试

运行栅格处理测试：

```bash
cd backend/sample_data

# 基础栅格功能测试（DEM、土地利用）
python test_raster_processing.py

# 增强功能测试（坡向计算、栅格代数）
python test_raster_enhancements.py
```

### 基础测试内容（test_raster_processing.py）

1. 生成示例 DEM（200×200 像元）
2. 生成示例土地利用栅格
3. 裁剪到分析边界
4. 计算坡度
5. 对网格单元进行分区统计
6. 提取地形特征和土地利用特征

### 增强功能测试内容（test_raster_enhancements.py）

1. **坡向计算测试**
   - 计算坡向（0-360度）
   - 8方向分类（北/东北/东/东南/南/西南/西/西北）
   - 4方向分类（北/东/南/西）
   - 阴阳坡分类（向阳坡/背阴坡/半阴半阳）

2. **栅格代数运算测试**
   - 简单算术：地形起伏度 = 高程/100 + 坡度
   - 条件运算：where(坡度<5, 1, 0)
   - 标准化运算：(坡度 - 均值) / 标准差
   - 复合指数：0.6×标准化高程 + 0.4×标准化坡度

3. **DEM完整处理流程（含坡向）**
   - 提取高程、坡度、坡向统计
   - 计算主导坡向（8个方向）

输出文件：
- `aspect.tif` - 坡向栅格
- `terrain_roughness.tif` - 地形起伏度
- `flat_areas.tif` - 平坦区域标识
- `normalized_slope.tif` - 标准化坡度
- `terrain_composite_index.tif` - 地形综合指数
- `grid_with_terrain_aspect.geojson` - 带坡向特征的网格

## 集成到空间分析

在特征提取器中使用栅格数据：

```python
from backend.spatial_analysis.feature_extractor import FeatureExtractor
from backend.data_processor.raster_processor import process_dem_for_analysis

extractor = FeatureExtractor()

# 1. 提取矢量特征
features = extractor.extract_all_features(
    units=grid,
    poi_data=poi,
    roads_data=roads
)

# 2. 添加栅格特征（DEM）
if dem_path:
    terrain_features = process_dem_for_analysis(
        dem_path, boundary, grid
    )
    features = features.merge(
        terrain_features[['unit_id', 'elevation_mean', 'slope_mean']],
        on='unit_id'
    )

# 3. 添加土地利用特征
if landuse_path:
    landuse_features = process_landuse_raster(landuse_path, grid)
    features = features.merge(
        landuse_features[['unit_id', 'landuse_dominant']],
        on='unit_id'
    )
```

## 依赖

栅格处理依赖 `rasterio`:

```bash
pip install rasterio==1.3.9
```

已添加到 `requirements.txt`。

## 性能优化建议

1. **数据量控制**
   - 栅格分辨率不要过高（建议 10-30m）
   - 先裁剪到分析区域再处理

2. **坐标系**
   - 使用投影坐标系（UTM）进行几何计算更准确
   - 最后转换回 WGS84 用于展示

3. **分区统计优化**
   - 对大量单元使用多进程并行计算
   - 缓存处理结果避免重复计算

4. **内存管理**
   - 大栅格使用分块读取（rasterio windowed reading）
   - 及时释放不再使用的数据

## 常见问题

### Q1: 坐标系不匹配

确保栅格和矢量数据使用相同坐标系：

```python
# 检查坐标系
print(f"栅格坐标系: {src.crs}")
print(f"矢量坐标系: {gdf.crs}")

# 转换矢量坐标系
gdf = gdf.to_crs(src.crs)
```

### Q2: NoData 值处理

```python
# 读取时指定 nodata 值
with rasterio.open('dem.tif') as src:
    data = src.read(1)
    nodata = src.nodata
    
    # 掩膜 nodata
    valid_data = data[data != nodata]
```

### Q3: 内存不足

```python
# 使用窗口读取大栅格
from rasterio.windows import Window

with rasterio.open('large_raster.tif') as src:
    for ji, window in src.block_windows(1):
        data = src.read(1, window=window)
        # 处理数据块
```

## 后续扩展

计划支持：
1. ~~**坡向计算** - 地形分析（✅ 已实现）~~
2. ~~**栅格代数运算** - 复杂指标计算（✅ 已实现）~~
3. **可视域分析** - 景观评价
4. **多波段处理** - 遥感影像
5. **时间序列栅格** - 变化检测

## 更新日志

### v1.1.0 (2026-09-19)
- ✅ 新增 `calculate_aspect()` - 坡向计算（支持度数/弧度）
- ✅ 新增 `classify_aspect()` - 坡向分类（8方向/4方向/阴阳坡）
- ✅ 新增 `raster_calculator()` - 栅格代数运算引擎
- ✅ `process_dem_for_analysis()` 集成坡向分析（新增 `aspect_mean` 和 `aspect_dominant` 字段）
- ✅ 新增测试脚本 `test_raster_enhancements.py`