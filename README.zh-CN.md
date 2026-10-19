# 城市片区功能适宜性分析

**结合 GIS 空间分析、交互地图与知识图谱解释的城市功能适宜性分析原型。**

[English](README.md) · [已知问题](docs/KNOWN_ISSUES.md) · [数据来源](DATA_SOURCES.md)

## 项目介绍

判断一片区域适合承担什么城市功能，需要同时考虑交通、周边设施、环境条件及相邻区域之间的关系。这个项目尝试把这些判断组织成可查看、可追溯的分析过程。

使用者上传自己的研究边界、POI 和可选路网数据，系统按同一套流程分析不同研究区域。上传数据需符合支持的格式；附带数据仅供演示，不限定研究地点。

系统将上传的研究区域划分为网格，提取空间指标，按可配置的规则计算不同功能的适宜性得分，并通过地图展示推荐结果。知识图谱连接分析单元、指标和功能，为结果查询及原因解释提供支持。

**当前为 Alpha 原型。** 前端界面及生成的解释以中文为主。各项能力在界面和 API 中的接入情况见[实现范围说明](docs/KNOWN_ISSUES.md)。

## 主要组成

| 模块 | 实现内容 |
| --- | --- |
| 项目与数据管理 | 创建项目，上传研究边界、POI 和可选路网。 |
| 空间处理 | 数据标准化、网格生成，提取距离、密度、可达性和几何指标。 |
| 适宜性评价 | 使用 YAML 配置准则、权重和约束，进行多准则评分。 |
| 功能推荐 | 比较候选功能得分，并结合邻近单元进行空间协调。 |
| 地图交互 | 切换图层和功能评分，点击网格查看详情。 |
| 结果解释 | 通过关键词识别、知识图谱查询和文本模板生成解释。 |

实际配置的七类功能是：**居住、商业、办公、工业、公共服务、绿地休闲、综合**。

评价采用基于规则的多准则方法；现有问答接口没有调用外部大语言模型，核心流程不需要 LLM API Key。

## 交互流程

1. 创建项目，上传边界和 POI 数据。
2. 添加路网，选择网格尺寸。
3. 提交分析任务并查看进度。
4. 在地图上查看功能推荐和各项评分。
5. 在成功生成知识图谱后，查询区域或单元的结果。

问题示例：

- `哪些区域适合商业开发？`
- `为什么单元 UNIT_0001 适合居住？`（使用结果中真实存在的单元编号。）
- `整体分析结果如何？`

对比查询需要通过 API 显式提供 `unit_ids`；当前聊天输入框不会提交这个字段。

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 前端 | HTML、CSS、原生 JavaScript、Leaflet |
| 后端 | Python、FastAPI、Uvicorn |
| 空间处理 | GeoPandas、Shapely、PyProj、Rtree、Rasterio |
| 数值分析 | NumPy、Pandas、SciPy |
| 规则与图谱工具 | PyYAML、自定义知识图谱模块、NetworkX、PyVis |
| 存储 | 本地项目目录、GeoJSON、JSON |

当前入口是 `frontend/index.html`，加载 `frontend/app.js`。保留的 `frontend/js/` 是另一套实现，当前页面没有加载它。

## 本地安装与启动

现有依赖建议配合 **Python 3.10 或 3.11** 使用。这是兼容性建议，不代表已完成全新环境安装验证。固定的 NumPy 1.24 系列[官方支持范围截至 Python 3.11](https://numpy.org/doc/1.24/release/1.24.0-notes.html)。

在项目根目录创建虚拟环境并安装依赖。

**Windows 命令提示符（CMD）**

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r backend/requirements.txt
```

**macOS / Linux**

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
```

在已激活环境的终端启动后端：

```bash
cd backend
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

另开终端，回到项目根目录，激活同一个环境后启动前端：

```bash
cd frontend
python -m http.server 8080 --bind 127.0.0.1
```

- 前端：[http://localhost:8080](http://localhost:8080)
- API 文档：[http://localhost:8000/docs](http://localhost:8000/docs)
- 健康检查：[http://localhost:8000/health](http://localhost:8000/health)

前端固定连接本机 8000 端口。Leaflet CDN 和当前使用的高德底图需要网络连接。上述流程用于本地开发，不是线上部署方案。

## 示例数据

建议先使用 `backend/test_data_osm/` 中的小范围 OSM 示例：

| 上传分类 | 文件 | 要素数量 |
| --- | --- | ---: |
| 边界（必需） | `boundary.geojson` | 1 |
| POI（必需） | `poi.geojson` | 1,351 |
| 路网（可选） | `roads.geojson` | 2,352 |

矢量上传接口支持 GeoJSON 和 ZIP 格式的 Shapefile。其他栅格及约束数据尚未全部接入网页分析流程，详见[已知问题](docs/KNOWN_ISSUES.md)。

`backend/sample_data/` 保留了合成样例和生成脚本。重新生成边界、POI 和道路样例时，请**在项目根目录**执行：

```bash
python backend/sample_data/generate_sample_area.py
python backend/sample_data/generate_sample_poi.py
python backend/sample_data/generate_sample_roads.py
```

这些命令可能覆盖已有合成样例。请使用同一研究区域的边界、POI 和路网，不要混用合成样例与 OSM 示例。

## 文件导航

| 路径 | 用途 |
| --- | --- |
| `backend/api/` | 项目管理、数据上传、任务执行及问答接口 |
| `backend/data_processor/` | 标准化、网格、栅格与矢量约束处理 |
| `backend/spatial_analysis/` | 指标提取、评价和推荐 |
| `backend/spatial_analysis/function_rules.yaml` | 功能规则、权重和约束 |
| `backend/kg/` | 知识图谱构建、推理及文本解释 |
| `backend/test_data_osm/` | 小范围真实输入样例 |
| `backend/sample_data/` | 合成数据与生成脚本 |
| `frontend/` | 界面和地图交互 |
| `docs/` | 当前问题记录及上传说明 |

缓存、字节码、历史项目数据及大型中间结果不包含在整理版中，并已加入 `.gitignore`。程序启动时会创建项目存储目录。

## 当前范围

- 得分受人工规则、代理指标和缺失值默认值影响，属于探索性指标，不是经过验证的规划结论或统计概率。
- 当前界面提交方形网格，并关闭地形分析；后端模块中的其他能力不等于已全部接入界面。
- 本次文档整理未进行全新环境的端到端运行测试，不据此判断系统能否完整运行，也不新增准确率、运行速度或规模上限的声明。
- 原阶段总结及技术方案保留为开发记录，完成状态可能与当前代码不一致。当前范围以本 README 和已知问题说明为准。

## 文档与来源

- [已知问题](docs/KNOWN_ISSUES.md)
- [数据来源及第三方组件](DATA_SOURCES.md)
- [后端 API 开发记录](backend/README_API.md)
- [原技术方案](项目技术方案.md)
- [GitHub 上传说明](docs/PUBLISHING.zh-CN.md)

OSM 示例数据：© OpenStreetMap contributors，采用 [Open Database License](https://opendatacommons.org/licenses/odbl/1-0/)，参见 [OpenStreetMap 署名说明](https://www.openstreetmap.org/copyright)。

本快照没有独立的软件 `LICENSE` 文件。原 README 曾写明 MIT，具体软件许可应由权利人确认；第三方数据和依赖保留各自许可。
