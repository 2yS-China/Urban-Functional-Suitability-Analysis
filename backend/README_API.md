# FastAPI 后端服务文档

## 概览

基于FastAPI构建的城市片区功能适宜性分析系统后端服务，提供完整的RESTful API接口。

## 启动服务

```bash
cd backend
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

服务启动后，访问以下地址：

- **API文档（Swagger）**: http://localhost:8000/docs
- **API文档（ReDoc）**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/health

## API模块结构

```
api/
├── main.py                  # FastAPI应用入口
├── project_manager.py       # 项目管理服务
├── analysis_worker.py       # 分析任务工作器
├── schemas.py              # 通用响应模型
└── routes/                 # 路由模块
    ├── project_routes.py   # 项目管理API
    ├── data_routes.py      # 数据上传API
    ├── analysis_routes.py  # 分析任务API
    └── qa_routes.py        # 知识问答API
```

## API接口清单

### 1. 项目管理 API (`/api/projects`)

#### 创建项目
```http
POST /api/projects
Content-Type: application/json

{
  "name": "示例项目",
  "description": "项目描述"
}
```

**响应：**
```json
{
  "success": true,
  "message": "项目创建成功",
  "data": {
    "id": "示例项目_20260919_123456",
    "name": "示例项目",
    "description": "项目描述",
    "created_at": "2026-09-19T12:34:56",
    "updated_at": "2026-09-19T12:34:56",
    "status": "created",
    "data_status": {
      "boundary": false,
      "poi": false,
      "roads": false
    },
    "analysis_status": null
  }
}
```

#### 列出所有项目
```http
GET /api/projects?skip=0&limit=100
```

#### 获取项目详情
```http
GET /api/projects/{project_id}
```

#### 更新项目
```http
PUT /api/projects/{project_id}
Content-Type: application/json

{
  "name": "新项目名称",
  "description": "新描述"
}
```

#### 删除项目
```http
DELETE /api/projects/{project_id}
```

### 2. 数据上传 API (`/api/projects/{project_id}/data`)

#### 上传地理数据
```http
POST /api/projects/{project_id}/data/{data_type}
Content-Type: multipart/form-data

file: [GeoJSON或Shapefile ZIP文件]
description: "数据描述"（可选）
```

**支持的data_type：**
- `boundary` - 边界数据（Polygon/MultiPolygon）
- `poi` - POI点位数据（Point/MultiPoint）
- `roads` - 路网数据（LineString/MultiLineString）
- `dem` - DEM地形数据（TIF栅格）
- `landuse` - 土地利用数据（TIF栅格）

**支持的文件格式：**
- GeoJSON (.geojson, .json)
- Shapefile (.zip，需包含.shp, .shx, .dbf等文件)
- GeoTIFF (.tif, .tiff，仅DEM和landuse）

**响应：**
```json
{
  "success": true,
  "message": "boundary数据上传成功",
  "data": {
    "file_name": "boundary.geojson",
    "file_size": 12345,
    "data_type": "boundary",
    "stats": {
      "feature_count": 1,
      "crs": "EPSG:4326",
      "geometry_types": ["Polygon"],
      "bounds": [113.0, 23.0, 114.0, 24.0],
      "columns": ["name", "geometry"]
    },
    "saved_path": "项目ID/raw/boundary_boundary.geojson"
  }
}
```

#### 查询数据状态
```http
GET /api/projects/{project_id}/data/status
```

#### 删除数据
```http
DELETE /api/projects/{project_id}/data/{data_type}
```

### 3. 分析任务 API

#### 启动分析任务
```http
POST /api/projects/{project_id}/analyze
Content-Type: application/json

{
  "grid_mode": "square",           // square/hexagon/parcel
  "grid_size": 100,                // 50-500米
  "buffer_radius": 500,            // 100-2000米
  "include_terrain": false,        // 是否包含地形分析
  "build_knowledge_graph": true    // 是否构建知识图谱
}
```

**响应：**
```json
{
  "success": true,
  "message": "分析任务创建成功",
  "data": {
    "task_id": "uuid",
    "project_id": "项目ID",
    "status": "pending",
    "message": "分析任务已启动"
  }
}
```

#### 查询任务状态
```http
GET /api/tasks/{task_id}
```

**响应：**
```json
{
  "success": true,
  "data": {
    "task_id": "uuid",
    "project_id": "项目ID",
    "status": "processing",      // pending/processing/completed/failed
    "progress": 50,              // 0-100
    "message": "提取空间特征",
    "created_at": "2026-09-19T12:34:56",
    "updated_at": "2026-09-19T12:35:00",
    "result": null,
    "error": null
  }
}
```

#### 获取分析结果
```http
GET /api/projects/{project_id}/results
```

**响应：**
```json
{
  "success": true,
  "data": {
    "project_id": "项目ID",
    "geojson": { /* GeoJSON Feature Collection */ },
    "statistics": {
      "total_units": 120,
      "function_counts": {
        "居住": 45,
        "商业": 30,
        "办公": 25
      },
      "function_areas": { /* 面积统计 */ },
      "score_statistics": { /* 得分统计 */ }
    },
    "knowledge_graph": { /* 知识图谱JSON */ },
    "analysis_status": "completed"
  }
}
```

#### 列出项目的所有任务
```http
GET /api/projects/{project_id}/tasks
```

### 4. 知识问答 API

#### 提问
```http
POST /api/projects/{project_id}/qa
Content-Type: application/json

{
  "question": "为什么单元A适合居住？",
  "question_type": "explain",    // 可选，自动识别
  "unit_id": "unit_001",        // 针对特定单元
  "function_type": null,        // 查询类问题需要
  "unit_ids": null              // 对比类问题需要
}
```

**问题类型：**
- `explain` - 解释单元适宜性，如"为什么单元A适合居住？"
- `query` - 查询适宜区域，如"哪些区域适合商业？"
- `compare` - 对比多个单元，如"对比单元A和B"
- `overview` - 整体概览，如"整体分析结果如何？"

**响应：**
```json
{
  "success": true,
  "data": {
    "question": "为什么单元A适合居住？",
    "answer": "单元unit_001非常适合居住功能...",
    "question_type": "explain",
    "related_units": ["unit_001"],
    "metadata": {
      "recommended_function": "居住"
    }
  }
}
```

#### 获取知识图谱
```http
GET /api/projects/{project_id}/knowledge-graph
```

**响应：**
```json
{
  "success": true,
  "data": {
    "knowledge_graph": {
      "nodes": [ /* 节点列表 */ ],
      "edges": [ /* 边列表 */ ]
    },
    "statistics": {
      "node_count": 150,
      "edge_count": 500,
      "unit_count": 120,
      "function_types": ["居住", "商业", "办公"]
    }
  }
}
```

## 错误处理

所有API错误响应遵循统一格式：

```json
{
  "success": false,
  "message": "错误消息",
  "detail": "详细错误信息",
  "timestamp": "2026-09-19T12:34:56"
}
```

**HTTP状态码：**
- `200` - 成功
- `201` - 创建成功
- `202` - 已接受（异步任务）
- `400` - 请求参数错误
- `404` - 资源不存在
- `500` - 服务器内部错误

## 数据流程

完整的分析流程：

1. **创建项目** → `POST /api/projects`
2. **上传边界数据** → `POST /api/projects/{id}/data/boundary`
3. **上传POI数据** → `POST /api/projects/{id}/data/poi`
4. **上传路网数据（可选）** → `POST /api/projects/{id}/data/roads`
5. **启动分析** → `POST /api/projects/{id}/analyze`
6. **轮询任务状态** → `GET /api/tasks/{task_id}`
7. **获取结果** → `GET /api/projects/{id}/results`
8. **知识问答** → `POST /api/projects/{id}/qa`

## 配置

### 文件大小限制
- 单个文件最大：50MB（`ProjectConfig.MAX_UPLOAD_SIZE_MB`）
- 单个项目最大：500MB（`ProjectConfig.MAX_PROJECT_SIZE_MB`）

### 数据存储
- 项目数据目录：`backend/data/projects/{project_id}/`
- 目录结构：
  - `raw/` - 原始上传数据
  - `processed/` - 处理后的数据
  - `results/` - 分析结果
  - `exports/` - 导出文件
  - `metadata.json` - 项目元数据
  - `task_{uuid}.json` - 任务元数据

## 测试

### 启动测试
```bash
cd backend
python test_api_startup.py
```

### API集成测试（待实现）
```bash
cd backend
pytest tests/test_api_integration.py
```

## 依赖

核心依赖（见 `requirements.txt`）：
- FastAPI - Web框架
- Uvicorn - ASGI服务器
- Pydantic - 数据验证
- GeoPandas - GIS数据处理
- Rasterio - 栅格数据处理

## Phase 3完成状态

### 已完成：
- ✅ Phase 3.1: FastAPI项目搭建
- ✅ Phase 3.2: 项目管理API
- ✅ Phase 3.3: 数据上传API
- ✅ Phase 3.4: 分析任务API
- ✅ Phase 3.5: 知识问答API

### 下一步（Phase 4）：
- 前端Vue 3项目搭建
- 基础组件开发
- 状态管理
- API集成

## 注意事项

1. **CORS配置**：当前允许所有来源（`allow_origins=["*"]`），生产环境需要限制
2. **文件上传**：Shapefile必须打包为ZIP，且包含所有必需文件（.shp, .shx, .dbf）
3. **坐标系**：系统默认使用WGS84（EPSG:4326），上传时会自动检测和转换
4. **异步任务**：分析任务采用后台任务处理，需要轮询任务状态
5. **知识图谱**：需要先完成分析才能进行问答