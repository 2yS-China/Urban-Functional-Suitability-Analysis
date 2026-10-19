# 15个核心评价指标扩展 - 实施说明

## 一、扩展概述

本次扩展将原有的简化特征体系升级为完整的15个核心评价指标体系，符合城市规划领域的专业要求。

### 15个核心指标分类

#### 1. 地形地质类（3个）
- **高程**（elevation_mean）：平均高程，影响建设成本和排水
- **坡度**（slope_mean）：平均坡度，影响建设适宜性
- **地质灾害易发性**（geological_hazard_level, geological_safety_score）：滑坡、崩塌等地质灾害风险

#### 2. 气候环境类（1个）
- **年降水量**（annual_precipitation）：影响绿化、排水设计

#### 3. 水资源类（1个）
- **距水体距离**（dist_to_water, water_proximity）：临水性，影响景观和生态价值

#### 4. 土地资源类（1个）
- **土壤类型**（soil_type, soil_agri_suitability, soil_const_suitability）：影响农业和建设适宜性

#### 5. 交通可达性类（1个）
- **交通可达性**（road_accessibility）：综合交通便利度

#### 6. 人口与社会类（2个）
- **人口密度**（population_density_1000m）：服务需求强度
- **基础设施密度**（poi_density系列）：现有配套水平

#### 7. 经济类（1个）
- **GDP密度**（gdp_density, economic_vitality）：经济活力

#### 8. 保护约束类（2个）
- **生态红线范围**（in_ecological_redline, ecological_constraint）：生态保护硬约束
- **基本农田保护区**（in_farmland_protection, farmland_constraint）：农田保护硬约束

#### 9. 建设现状类（1个）
- **建成区缓冲距离**（dist_to_built_edge, built_buffer_zone）：城市扩展阶段

#### 10. 灾害风险类（1个）
- **洪涝灾害风险**（flood_risk_level, flood_safety_score）：水灾风险

#### 11. 城市结构类（1个）
- **城市中心辐射强度**（city_center_radiation_normalized）：中心性和可达性

---

## 二、技术实施

### 1. 数据模型扩展

#### 1.1 字段映射配置（field_mapping.yaml）
新增栅格类型：
- precipitation（年降水量）
- soil_type（土壤类型）
- gdp_density（GDP密度）
- flood_risk（洪涝风险）
- geological_hazard（地质灾害）

新增矢量约束类型：
- water_bodies（水体）
- ecological_redline（生态红线）
- farmland_protection（基本农田）
- built_area（建成区）
- city_center（城市中心）

#### 1.2 栅格处理模块（raster_processor_extended.py）
新增处理函数：
- `process_precipitation_raster()` - 年降水量处理
- `process_soil_type_raster()` - 土壤类型处理
- `process_gdp_density_raster()` - GDP密度处理
- `process_flood_risk_raster()` - 洪涝风险处理
- `process_geological_hazard_raster()` - 地质灾害处理

#### 1.3 矢量约束模块（vector_constraints.py）
新增处理函数：
- `process_water_bodies()` - 水体距离和临水性
- `process_ecological_redline()` - 生态红线约束
- `process_farmland_protection()` - 基本农田约束
- `process_built_area()` - 建成区缓冲分析
- `process_city_center()` - 城市中心辐射强度

### 2. 特征提取扩展

#### 2.1 特征提取器（feature_extractor.py）
扩展`extract_all_features()`方法，新增参数：
```python
def extract_all_features(
    units,
    poi_data, roads_data,  # 原有
    dem_path, precipitation_path, soil_path, gdp_path,  # 新增栅格
    flood_path, hazard_path,  # 新增栅格
    water_path, redline_path, farmland_path,  # 新增矢量
    built_path, center_path  # 新增矢量
)
```

新增两个私有方法：
- `_extract_raster_features()` - 调用栅格处理模块
- `_extract_constraint_features()` - 调用矢量约束模块

### 3. 评价规则更新

#### 3.1 居住功能规则（function_rules.yaml）
调整权重分配，新增指标：
- 地质安全性（geological_safety_score）权重 0.06
- 洪涝安全性（flood_safety_score）权重 0.06
- 高程（elevation_mean）权重 0.03
- 坡度（slope_mean）权重 0.06
- 城市中心辐射（city_center_radiation_normalized）权重 0.05
- 建成区缓冲（built_buffer_zone）权重 0.05

新增硬约束：
- 不能在生态红线内（in_ecological_redline ≤ 0）
- 不能在基本农田内（in_farmland_protection ≤ 0）
- 洪涝安全性 ≥ 0.5
- 地质安全性 ≥ 0.5

#### 3.2 商业、办公、工业功能规则
类似调整，增加GDP密度、城市中心辐射等指标权重。

#### 3.3 工业功能规则
新增土壤建设适宜性（soil_const_suitability）权重 0.08
新增约束：距离水体至少1000米（环保要求）

#### 3.4 绿地休闲功能规则
新增土壤绿化适宜性（soil_agri_suitability）权重 0.08
新增年降水量（annual_precipitation）权重 0.05

### 4. 知识图谱扩展

#### 4.1 节点类型（NodeType枚举）
新增：`CONSTRAINT = "constraint"` - 约束节点

#### 4.2 约束节点类（ConstraintNode）
属性：
- constraint_type：约束类型（ecological_redline, farmland, flood_risk等）
- severity：严重程度（strict, strong, moderate, soft）
- description：约束描述
- affected_functions：受影响的功能类型列表

#### 4.3 关系类型（RelationType枚举）
新增：
- `CONSTRAINED_BY = "受约束"` - 单元受约束影响
- `CONFLICTS_WITH = "冲突"` - 功能与约束冲突

### 5. API和前端更新

#### 5.1 数据上传API（data_routes.py）
扩展DATA_TYPES列表至16种：
```python
DATA_TYPES = [
    "boundary", "poi", "roads",  # 基础
    "dem", "precipitation", "landuse", "soil_type",  # 栅格
    "gdp_density", "flood_risk", "geological_hazard",  # 栅格
    "water_bodies", "ecological_redline",  # 矢量约束
    "farmland_protection", "built_area", "city_center"  # 矢量约束
]
```

新增分类常量：
- RASTER_DATA_TYPES - 7种栅格类型
- VECTOR_DATA_TYPES - 9种矢量类型

扩展几何类型验证：
- water_bodies, ecological_redline, farmland_protection, built_area: Polygon
- city_center: Point

#### 5.2 前端数据上传界面（app.js）
重构`updateDataUploadArea()`函数：
- 按类别分组显示（8个类别）
- 16种数据类型，每种明确标注文件格式

8个类别：
1. 基础数据（boundary, poi）
2. 交通可达性（roads）
3. 地形地质（dem）
4. 气候环境（precipitation）
5. 土地资源（landuse, soil_type）
6. 水资源（water_bodies）
7. 经济指标（gdp_density）
8. 保护区约束（ecological_redline, farmland_protection）
9. 建设现状（built_area）
10. 灾害风险（flood_risk, geological_hazard）
11. 城市结构（city_center）

---

## 三、使用说明

### 1. 数据准备要求

**重要说明**：用户只需上传原始数据文件，系统会自动计算派生特征。15个核心指标中的大部分是通过空间计算得出，不是直接上传。

#### 栅格数据（.tif/.tiff）- 提取统计特征
- **DEM**：数字高程模型，单位米
  - 系统自动计算：平均高程、坡度、坡向
  
- **precipitation**：年降水量栅格，单位毫米
  - 系统自动计算：平均降水量、降水适宜性指数
  
- **soil_type**：土壤类型栅格，值域1-5
  - 1=砂土, 2=壤土, 3=粘土, 4=有机土, 5=盐碱土
  - 系统自动计算：主导土壤类型、农业适宜性、建设适宜性
  
- **gdp_density**：GDP密度栅格，单位万元/km²
  - 系统自动计算：平均GDP密度、经济活力指数
  
- **flood_risk**：洪涝风险栅格，值域1-5
  - 1=低风险, 2=中低, 3=中等, 4=中高, 5=高风险
  - 系统自动计算：风险等级、安全性评分
  
- **geological_hazard**：地质灾害易发性栅格，值域1-5
  - 1=不易发, 2=低易发, 3=中易发, 4=高易发, 5=极高易发
  - 系统自动计算：易发性等级、安全性评分
  
- **landuse**：土地利用栅格，值域1-6
  - 1=耕地, 2=林地, 3=草地, 4=水域, 5=建设用地, 6=未利用地
  - 系统自动计算：各类用地占比、主导用地类型

#### 矢量数据（.geojson/.json/.zip）- 进行空间计算
- **boundary**：分析边界（Polygon）**[必需]**
  - 用途：定义分析范围，生成网格
  
- **poi**：兴趣点（Point）**[必需]**
  - 用途：推算人口密度、统计设施密度
  - 系统自动计算：
    - population_density（从居住POI推算）
    - poi_density_*（各类设施密度）
    - 聚集度指标
  
- **roads**：路网（LineString）
  - 要求：需包含road_level字段（1=快速路, 2=主干道, 3=次干道, 4=支路）
  - 系统自动计算：
    - dist_to_road_level_*（到各级道路的距离）
    - road_accessibility（综合交通可达性，加权计算）
  
- **water_bodies**：水体（Polygon）
  - 包含：河流、湖泊、水库等
  - 系统自动计算：
    - dist_to_water（到最近水体的距离）
    - water_proximity（临水性指数，距离越近越高）
  
- **ecological_redline**：生态保护红线（Polygon）
  - 系统自动计算：
    - in_ecological_redline（是否在红线内，0/1）
    - dist_to_ecological_redline（到红线的距离）
    - ecological_constraint（生态约束强度）
  
- **farmland_protection**：基本农田保护区（Polygon）
  - 系统自动计算：
    - in_farmland_protection（是否在保护区内）
    - dist_to_farmland（到农田的距离）
    - farmland_constraint（农田约束强度）
  
- **built_area**：建成区范围（Polygon）
  - 系统自动计算：
    - in_built_area（是否在建成区内）
    - dist_to_built_edge（到建成区边界的距离，负值=内部，正值=外部）
    - built_buffer_zone（缓冲带等级：0远郊/1近郊/2边缘/3核心）
  
- **city_center**：城市中心点（Point）
  - 可包含多个中心点，支持importance字段（重要性权重）
  - 系统自动计算：
    - dist_to_city_center（到最近中心的距离）
    - city_center_radiation（多中心叠加辐射强度）
    - city_center_radiation_normalized（归一化辐射强度，0-1）

### 2. 数据上传流程

1. **创建项目**
2. **上传必需数据**：boundary（边界）, poi（兴趣点）
3. **上传可选数据**：根据分析需求选择上传相关数据
   - 如需评估交通便利性 → 上传roads
   - 如需考虑地形限制 → 上传dem
   - 如需考虑生态约束 → 上传ecological_redline
   - 如需评估临水景观 → 上传water_bodies
   - 其他数据类推
4. **启动分析任务**：系统自动执行特征计算和适宜性评价

### 3. 特征提取说明

**自动化计算流程**：
1. 系统检测已上传的数据类型
2. 根据数据类型自动调用对应的处理模块：
   - 栅格数据 → 栅格统计分析（均值、主导值、分级）
   - 矢量数据 → 空间关系计算（距离、密度、缓冲、叠加）
3. 生成40+个派生特征，覆盖15个核心指标
4. 如果某些数据缺失，相关特征使用默认值

**示例：交通可达性计算**
```
用户上传：roads.geojson（包含道路线和road_level字段）
    ↓
系统处理：
  1. 计算每个网格到各级道路的最小距离
     - dist_to_road_level_1（到快速路距离）
     - dist_to_road_level_2（到主干道距离）
     - dist_to_road_level_3（到次干道距离）
     - dist_to_road_level_4（到支路距离）
  2. 加权计算综合可达性
     road_accessibility = 0.4×exp(-d1/1000) + 0.3×exp(-d2/1000) 
                        + 0.2×exp(-d3/1000) + 0.1×exp(-d4/1000)
    ↓
输出特征：road_accessibility（0-1，值越大越便利）
```

**示例：距水体距离计算**
```
用户上传：water_bodies.geojson（水体面状数据）
    ↓
系统处理：
  1. 计算每个网格质心到最近水体边界的距离
     dist_to_water = min(distance(centroid, water_polygon))
  2. 计算临水性指数（指数衰减）
     water_proximity = exp(-dist_to_water / 500)
    ↓
输出特征：
  - dist_to_water（距离，单位米）
  - water_proximity（临水性，0-1，距离越近越高）
```

### 4. 评价规则应用

每个功能类型的评价规则会根据可用特征动态调整：
- 如果特征存在，使用配置的权重
- 如果特征缺失，重新归一化其他特征权重
- 硬约束：如果约束特征存在且违反，该功能评分直接降为0

---

## 四、技术架构图

```
数据输入
├── 矢量数据（9种）
│   ├── boundary, poi, roads
│   ├── water_bodies
│   ├── ecological_redline, farmland_protection
│   ├── built_area
│   └── city_center
└── 栅格数据（7种）
    ├── dem, landuse
    ├── precipitation, soil_type
    ├── gdp_density
    └── flood_risk, geological_hazard

         ↓

数据处理层
├── 标准化（normalizer.py）
├── 栅格处理（raster_processor.py + raster_processor_extended.py）
└── 矢量约束（vector_constraints.py）

         ↓

特征提取层（feature_extractor.py）
├── 区位特征（距离）
├── 环境特征（密度）
├── 交通特征（可达性）
├── 栅格特征（15个指标中的7个）
└── 约束特征（15个指标中的4个）

         ↓

空间分析层
├── 评价规则（function_rules.yaml）- 15指标权重配置
├── 适宜性评价（suitability_evaluator.py）
└── 功能推荐（recommender.py）

         ↓

知识图谱层
├── 节点：unit, poi, function, constraint
├── 关系：适宜、约束、冲突
└── 推理：多跳查询、证据链

         ↓

结果输出
├── 适宜性评分（7种功能）
├── 功能推荐
├── 自然语言解释
└── 可视化地图
```

---

## 五、文件清单

### 新增文件
1. `backend/data_processor/raster_processor_extended.py` - 扩展栅格处理
2. `backend/data_processor/vector_constraints.py` - 矢量约束处理

### 修改文件
1. `backend/data_processor/field_mapping.yaml` - 数据类型定义扩展
2. `backend/spatial_analysis/feature_extractor.py` - 特征提取方法扩展
3. `backend/spatial_analysis/function_rules.yaml` - 评价规则15指标权重
4. `backend/kg/knowledge_graph_builder.py` - 约束节点和关系
5. `backend/api/routes/data_routes.py` - 16种数据类型支持
6. `frontend/app.js` - 分类上传界面

---

## 六、后续建议

### 1. 测试数据准备
建议准备完整的测试数据集，包含全部16种数据类型，验证完整流程。

### 2. 权重校准
15个指标的权重配置基于经验值，建议根据实际案例调整：
- 使用专家打分法确定各指标权重
- 使用AHP层次分析法优化权重结构
- 通过历史规划案例回测验证

### 3. 知识图谱推理增强
可进一步扩展推理规则，例如：
- 如果单元在生态红线内 AND 适宜居住 → 冲突警告
- 如果单元洪涝风险高 AND 人口密度高 → 风险预警

### 4. 可视化增强
前端可增加：
- 指标雷达图对比
- 约束叠加显示
- 多情景对比分析

---

## 七、版本记录

- **v2.0** - 15个核心指标扩展（2024）
  - 新增9种数据类型
  - 扩展评价规则体系
  - 增强知识图谱约束建模
  
- **v1.0** - 基础版本（2024）
  - 5种数据类型（boundary, poi, roads, dem, landuse）
  - 21维特征
  - 7种功能评价